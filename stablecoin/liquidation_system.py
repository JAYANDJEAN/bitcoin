"""
清算系统模块

监控抵押品价值，自动执行清算操作，维护系统稳定性。
"""

import time
from typing import Dict, List, Optional, Set, Tuple
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum

# 设置精度
getcontext().prec = 50


class LiquidationStatus(Enum):
    """清算状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LiquidationEvent:
    """清算事件"""
    liquidation_id: str
    position_id: str
    liquidator: str
    collateral_type: str
    collateral_amount: Decimal
    debt_amount: Decimal
    liquidation_price: Decimal
    penalty_amount: Decimal
    bonus_amount: Decimal  # 清算奖励
    timestamp: float
    status: LiquidationStatus = LiquidationStatus.PENDING

    def __post_init__(self):
        """初始化后处理"""
        self.collateral_amount = Decimal(str(self.collateral_amount))
        self.debt_amount = Decimal(str(self.debt_amount))
        self.liquidation_price = Decimal(str(self.liquidation_price))
        self.penalty_amount = Decimal(str(self.penalty_amount))
        self.bonus_amount = Decimal(str(self.bonus_amount))


@dataclass
class LiquidationCandidate:
    """清算候选"""
    position_id: str
    owner: str
    collateral_type: str
    collateral_amount: Decimal
    debt_amount: Decimal
    current_ratio: Decimal
    liquidation_threshold: Decimal
    urgency_score: Decimal  # 紧急程度评分

    def __post_init__(self):
        """初始化后处理"""
        self.collateral_amount = Decimal(str(self.collateral_amount))
        self.debt_amount = Decimal(str(self.debt_amount))
        self.current_ratio = Decimal(str(self.current_ratio))
        self.liquidation_threshold = Decimal(str(self.liquidation_threshold))
        self.urgency_score = Decimal(str(self.urgency_score))


class LiquidationSystem:
    """清算系统"""

    def __init__(self, stablecoin, collateral_manager, price_oracle):
        self.stablecoin = stablecoin
        self.collateral_manager = collateral_manager
        self.price_oracle = price_oracle

        # 清算事件记录
        self.liquidation_events: Dict[str, LiquidationEvent] = {}
        self.liquidation_history: List[LiquidationEvent] = []

        # 清算器（可以执行清算的地址）
        self.liquidators: Set[str] = set()

        # 系统参数
        self.liquidation_bonus = Decimal('0.05')  # 5% 清算奖励
        self.max_liquidation_amount = Decimal('0.5')  # 最大清算比例50%
        self.liquidation_delay = 60  # 清算延迟（秒）

        # 清算统计
        self.total_liquidations = 0
        self.total_liquidated_collateral = Decimal('0')
        self.total_liquidated_debt = Decimal('0')

        # 事件日志
        self.events: List[Dict] = []

        print("✅ 清算系统已初始化")

    def register_liquidator(self, address: str) -> bool:
        """注册清算器"""
        try:
            if address in self.liquidators:
                raise ValueError(f"清算器 {address} 已注册")

            self.liquidators.add(address)

            # 记录事件
            event = {
                'type': 'liquidator_registered',
                'address': address,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 注册清算器: {address}")
            return True

        except Exception as e:
            print(f"❌ 注册清算器失败: {e}")
            return False

    def unregister_liquidator(self, address: str) -> bool:
        """注销清算器"""
        try:
            if address not in self.liquidators:
                raise ValueError(f"清算器 {address} 未注册")

            self.liquidators.remove(address)

            # 记录事件
            event = {
                'type': 'liquidator_unregistered',
                'address': address,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 注销清算器: {address}")
            return True

        except Exception as e:
            print(f"❌ 注销清算器失败: {e}")
            return False

    def scan_liquidation_candidates(self) -> List[LiquidationCandidate]:
        """扫描清算候选"""
        candidates = []

        try:
            # 遍历所有头寸
            for position_id, position in self.stablecoin.positions.items():
                # 获取抵押品价格
                price_data = self.price_oracle.get_price(position.collateral_type)
                if not price_data:
                    continue

                # 获取抵押品类型信息
                collateral_type = self.collateral_manager.get_collateral_type(
                    position.collateral_type)
                if not collateral_type:
                    continue

                # 计算当前抵押率
                collateral_value = position.collateral_amount * price_data.price
                if position.debt_amount <= 0:
                    continue

                current_ratio = collateral_value / position.debt_amount

                # 检查是否需要清算
                if current_ratio < collateral_type.liquidation_ratio:
                    # 计算紧急程度评分
                    urgency_score = self._calculate_urgency_score(
                        current_ratio, collateral_type.liquidation_ratio, position.debt_amount
                    )

                    candidate = LiquidationCandidate(
                        position_id=position_id,
                        owner=position.owner,
                        collateral_type=position.collateral_type,
                        collateral_amount=position.collateral_amount,
                        debt_amount=position.debt_amount,
                        current_ratio=current_ratio,
                        liquidation_threshold=collateral_type.liquidation_ratio,
                        urgency_score=urgency_score
                    )

                    candidates.append(candidate)

            # 按紧急程度排序
            candidates.sort(key=lambda x: x.urgency_score, reverse=True)

            return candidates

        except Exception as e:
            print(f"❌ 扫描清算候选失败: {e}")
            return []

    def _calculate_urgency_score(self, current_ratio: Decimal, threshold: Decimal,
                                 debt_amount: Decimal) -> Decimal:
        """计算紧急程度评分"""
        # 抵押率偏差
        ratio_factor = (threshold - current_ratio) / threshold

        # 债务规模因子
        debt_factor = debt_amount / Decimal('1000')  # 标准化债务

        # 综合评分
        urgency_score = ratio_factor * debt_factor

        return max(urgency_score, Decimal('0'))

    def liquidate_position(self, liquidator: str, position_id: str,
                           liquidation_amount: Optional[Decimal] = None) -> str:
        """执行清算"""
        try:
            if liquidator not in self.liquidators:
                raise ValueError(f"未授权的清算器: {liquidator}")

            # 获取头寸信息
            position = self.stablecoin.get_position(position_id)
            if not position:
                raise ValueError(f"头寸 {position_id} 不存在")

            # 获取价格和抵押品信息
            price_data = self.price_oracle.get_price(position.collateral_type)
            if not price_data:
                raise ValueError(f"无法获取 {position.collateral_type} 价格")

            collateral_type = self.collateral_manager.get_collateral_type(position.collateral_type)
            if not collateral_type:
                raise ValueError(f"无效的抵押品类型: {position.collateral_type}")

            # 检查是否需要清算
            collateral_value = position.collateral_amount * price_data.price
            current_ratio = collateral_value / position.debt_amount

            if current_ratio >= collateral_type.liquidation_ratio:
                raise ValueError("头寸无需清算")

            # 计算清算数量
            if liquidation_amount is None:
                # 默认清算50%债务
                liquidation_amount = position.debt_amount * self.max_liquidation_amount
            else:
                liquidation_amount = min(liquidation_amount,
                                         position.debt_amount * self.max_liquidation_amount)

            # 计算需要的抵押品数量
            required_collateral = liquidation_amount / price_data.price

            # 计算清算罚金和奖励
            penalty_amount = required_collateral * collateral_type.liquidation_penalty
            bonus_amount = required_collateral * self.liquidation_bonus

            # 生成清算ID
            liquidation_id = self._generate_liquidation_id()

            # 创建清算事件
            liquidation_event = LiquidationEvent(
                liquidation_id=liquidation_id,
                position_id=position_id,
                liquidator=liquidator,
                collateral_type=position.collateral_type,
                collateral_amount=required_collateral + penalty_amount,
                debt_amount=liquidation_amount,
                liquidation_price=price_data.price,
                penalty_amount=penalty_amount,
                bonus_amount=bonus_amount,
                timestamp=time.time(),
                status=LiquidationStatus.PROCESSING
            )

            # 执行清算操作
            if self._execute_liquidation(liquidation_event, position):
                liquidation_event.status = LiquidationStatus.COMPLETED
                print(f"✅ 清算成功: {liquidation_id}")
            else:
                liquidation_event.status = LiquidationStatus.FAILED
                print(f"❌ 清算失败: {liquidation_id}")

            # 存储清算事件
            self.liquidation_events[liquidation_id] = liquidation_event
            self.liquidation_history.append(liquidation_event)

            return liquidation_id

        except Exception as e:
            print(f"❌ 清算操作失败: {e}")
            return ""

    def _execute_liquidation(self, liquidation_event: LiquidationEvent, position) -> bool:
        """执行具体的清算操作"""
        try:
            # 1. 从头寸中扣除抵押品
            position.collateral_amount -= liquidation_event.collateral_amount
            position.debt_amount -= liquidation_event.debt_amount

            # 2. 销毁清算器的稳定币
            if not self.stablecoin.burn(
                    liquidation_event.liquidator,
                    liquidation_event.debt_amount):
                return False

            # 3. 给清算器抵押品奖励
            collateral_reward = liquidation_event.collateral_amount - liquidation_event.penalty_amount
            if not self.collateral_manager.deposit_collateral(
                liquidation_event.liquidator,
                liquidation_event.collateral_type,
                collateral_reward
            ):
                return False

            # 4. 更新统计数据
            self.total_liquidations += 1
            self.total_liquidated_collateral += liquidation_event.collateral_amount
            self.total_liquidated_debt += liquidation_event.debt_amount

            # 5. 记录事件
            event = {
                'type': 'liquidation_executed',
                'liquidation_id': liquidation_event.liquidation_id,
                'position_id': liquidation_event.position_id,
                'liquidator': liquidation_event.liquidator,
                'debt_amount': liquidation_event.debt_amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            return True

        except Exception as e:
            print(f"❌ 执行清算操作失败: {e}")
            return False

    def _generate_liquidation_id(self) -> str:
        """生成清算ID"""
        import hashlib
        data = f"liquidation_{time.time()}_{len(self.liquidation_events)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_liquidation_event(self, liquidation_id: str) -> Optional[LiquidationEvent]:
        """获取清算事件"""
        return self.liquidation_events.get(liquidation_id)

    def get_liquidation_history(self, limit: int = 100) -> List[LiquidationEvent]:
        """获取清算历史"""
        return self.liquidation_history[-limit:]

    def monitor_positions(self) -> Dict:
        """监控头寸状态"""
        candidates = self.scan_liquidation_candidates()

        result = {
            'total_positions': len(self.stablecoin.positions),
            'liquidation_candidates': len(candidates),
            'urgent_liquidations': len([c for c in candidates if c.urgency_score > Decimal('10')]),
            'candidates': candidates[:10]  # 返回前10个最紧急的
        }

        if candidates:
            print(f"⚠️ 发现 {len(candidates)} 个清算候选")
            for candidate in candidates[:5]:  # 显示前5个
                print(f"  头寸 {candidate.position_id}: 抵押率 {candidate.current_ratio:.3f} "
                      f"(阈值: {candidate.liquidation_threshold:.3f})")

        return result

    def auto_liquidate(self) -> List[str]:
        """自动清算"""
        liquidation_ids = []

        try:
            candidates = self.scan_liquidation_candidates()

            # 只处理最紧急的几个
            urgent_candidates = [c for c in candidates[:5] if c.urgency_score > Decimal('5')]

            for candidate in urgent_candidates:
                # 选择一个清算器（简单起见，使用第一个）
                if self.liquidators:
                    liquidator = list(self.liquidators)[0]
                    liquidation_id = self.liquidate_position(liquidator, candidate.position_id)
                    if liquidation_id:
                        liquidation_ids.append(liquidation_id)

            if liquidation_ids:
                print(f"✅ 自动执行了 {len(liquidation_ids)} 次清算")

            return liquidation_ids

        except Exception as e:
            print(f"❌ 自动清算失败: {e}")
            return []

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        return {
            'total_liquidators': len(self.liquidators),
            'total_liquidations': self.total_liquidations,
            'total_liquidated_collateral': self.total_liquidated_collateral,
            'total_liquidated_debt': self.total_liquidated_debt,
            'liquidation_bonus': self.liquidation_bonus,
            'max_liquidation_amount': self.max_liquidation_amount,
            'pending_liquidations': len([e for e in self.liquidation_events.values()
                                         if e.status == LiquidationStatus.PENDING])
        }

    def print_status(self):
        """打印系统状态"""
        stats = self.get_system_stats()
        monitoring = self.monitor_positions()

        print(f"\n=== 清算系统状态 ===")
        print(f"注册清算器数量: {stats['total_liquidators']}")
        print(f"总清算次数: {stats['total_liquidations']}")
        print(f"清算奖励比例: {stats['liquidation_bonus']:.1%}")
        print(f"总头寸数量: {monitoring['total_positions']}")
        print(f"清算候选数量: {monitoring['liquidation_candidates']}")
        print(f"高风险头寸数量: {monitoring['urgent_liquidations']}")
