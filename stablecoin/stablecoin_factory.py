"""
稳定币工厂模块

统一管理稳定币系统的所有组件，提供完整的系统初始化和管理功能。
"""

import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, getcontext

from .stablecoin_core import StableCoin, StableCoinPosition
from .collateral_manager import CollateralManager, CollateralType
from .price_oracle import PriceOracle, PriceData
from .liquidation_system import LiquidationSystem, LiquidationEvent
from .governance import GovernanceSystem, Proposal, Vote

# 设置精度
getcontext().prec = 50


class StableCoinFactory:
    """稳定币工厂 - 统一管理所有组件"""

    def __init__(self, name: str = "DecentralizedUSD", symbol: str = "DUSD"):
        self.name = name
        self.symbol = symbol
        self.version = "1.0.0"
        self.created_at = time.time()

        # 初始化所有组件
        print(f"🚀 正在初始化 {name} 稳定币系统...")

        # 1. 初始化稳定币核心
        self.stablecoin = StableCoin(name, symbol)

        # 2. 初始化抵押品管理器
        self.collateral_manager = CollateralManager()

        # 3. 初始化价格预言机
        self.price_oracle = PriceOracle()

        # 4. 初始化清算系统
        self.liquidation_system = LiquidationSystem(
            self.stablecoin,
            self.collateral_manager,
            self.price_oracle
        )

        # 5. 初始化治理系统
        self.governance_system = GovernanceSystem(
            self.stablecoin,
            self.collateral_manager
        )

        # 系统管理员
        self.admins = {"admin", "factory_owner"}

        # 系统状态
        self.is_paused = False
        self.emergency_mode = False

        # 事件日志
        self.events: List[Dict] = []

        # 记录初始化事件
        event = {
            'type': 'system_initialized',
            'name': name,
            'symbol': symbol,
            'version': self.version,
            'timestamp': self.created_at
        }
        self.events.append(event)

        print(f"✅ {name} 稳定币系统初始化完成！")
        print(f"📊 系统版本: {self.version}")
        print(f"🔗 各组件已连接并准备就绪")

    def create_collateral_backed_position(self, user: str, collateral_type: str,
                                          collateral_amount: Decimal,
                                          borrow_amount: Decimal) -> str:
        """创建抵押品支持的稳定币头寸"""
        try:
            if self.is_paused:
                raise ValueError("系统已暂停")

            collateral_amount = Decimal(str(collateral_amount))
            borrow_amount = Decimal(str(borrow_amount))

            # 1. 检查抵押品类型
            collateral_info = self.collateral_manager.get_collateral_type(collateral_type)
            if not collateral_info:
                raise ValueError(f"不支持的抵押品类型: {collateral_type}")

            # 2. 获取价格
            price_data = self.price_oracle.get_price(collateral_type)
            if not price_data:
                raise ValueError(f"无法获取 {collateral_type} 价格")

            # 3. 检查抵押率
            collateral_value = collateral_amount * price_data.price
            collateral_ratio = collateral_value / borrow_amount

            if collateral_ratio < collateral_info.min_collateral_ratio:
                raise ValueError(f"抵押率不足，最低需要 {collateral_info.min_collateral_ratio}")

            # 4. 检查债务上限
            if not self.collateral_manager.check_debt_ceiling(collateral_type, borrow_amount):
                raise ValueError("超过债务上限")

            # 5. 锁定抵押品
            if not self.collateral_manager.lock_collateral(
                    user, collateral_type, collateral_amount):
                raise ValueError("锁定抵押品失败")

            # 6. 创建头寸
            position_id = self.stablecoin.create_position(
                user, collateral_type, collateral_amount, borrow_amount
            )

            if not position_id:
                # 回滚抵押品锁定
                self.collateral_manager.unlock_collateral(user, collateral_type, collateral_amount)
                raise ValueError("创建头寸失败")

            # 7. 铸造稳定币
            if not self.stablecoin.mint(user, borrow_amount, position_id):
                # 回滚操作
                self.collateral_manager.unlock_collateral(user, collateral_type, collateral_amount)
                del self.stablecoin.positions[position_id]
                raise ValueError("铸造稳定币失败")

            # 8. 记录事件
            event = {
                'type': 'position_created',
                'user': user,
                'position_id': position_id,
                'collateral_type': collateral_type,
                'collateral_amount': collateral_amount,
                'borrow_amount': borrow_amount,
                'collateral_ratio': collateral_ratio,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 为 {user} 创建头寸 {position_id}")
            print(f"   抵押品: {collateral_amount} {collateral_type}")
            print(f"   借出: {borrow_amount} {self.symbol}")
            print(f"   抵押率: {collateral_ratio:.2f}")

            return position_id

        except Exception as e:
            print(f"❌ 创建头寸失败: {e}")
            return ""

    def repay_and_withdraw(self, user: str, position_id: str,
                           repay_amount: Optional[Decimal] = None,
                           withdraw_amount: Optional[Decimal] = None) -> bool:
        """还款并提取抵押品"""
        try:
            if self.is_paused:
                raise ValueError("系统已暂停")

            # 获取头寸信息
            position = self.stablecoin.get_position(position_id)
            if not position:
                raise ValueError(f"头寸 {position_id} 不存在")

            if position.owner != user:
                raise ValueError("无权操作此头寸")

            # 默认全额还款
            if repay_amount is None:
                repay_amount = position.debt_amount
            else:
                repay_amount = Decimal(str(repay_amount))

            # 检查还款金额
            if repay_amount > position.debt_amount:
                repay_amount = position.debt_amount

            # 检查用户余额
            user_balance = self.stablecoin.balance_of(user)
            if user_balance < repay_amount:
                raise ValueError("稳定币余额不足")

            # 计算可提取的抵押品
            if repay_amount == position.debt_amount:
                # 全额还款，可提取所有抵押品
                max_withdraw = position.collateral_amount
            else:
                # 部分还款，需要保持最小抵押率
                collateral_info = self.collateral_manager.get_collateral_type(
                    position.collateral_type)
                price_data = self.price_oracle.get_price(position.collateral_type)

                if not collateral_info or not price_data:
                    raise ValueError("无法获取抵押品信息或价格")

                remaining_debt = position.debt_amount - repay_amount
                min_collateral_value = remaining_debt * collateral_info.min_collateral_ratio
                min_collateral_amount = min_collateral_value / price_data.price

                max_withdraw = position.collateral_amount - min_collateral_amount
                max_withdraw = max(max_withdraw, Decimal('0'))

            # 确定提取数量
            if withdraw_amount is None:
                withdraw_amount = max_withdraw
            else:
                withdraw_amount = Decimal(str(withdraw_amount))
                withdraw_amount = min(withdraw_amount, max_withdraw)

            # 执行还款
            if repay_amount > 0:
                if not self.stablecoin.burn(user, repay_amount):
                    raise ValueError("销毁稳定币失败")

                position.debt_amount -= repay_amount

            # 执行提取
            if withdraw_amount > 0:
                if not self.collateral_manager.unlock_collateral(
                    user, position.collateral_type, withdraw_amount
                ):
                    raise ValueError("解锁抵押品失败")

                position.collateral_amount -= withdraw_amount

            # 更新头寸
            position.last_updated = time.time()

            # 如果债务为0，删除头寸
            if position.debt_amount == 0:
                del self.stablecoin.positions[position_id]
                if user in self.stablecoin.user_positions:
                    self.stablecoin.user_positions[user].remove(position_id)

            # 记录事件
            event = {
                'type': 'repay_and_withdraw',
                'user': user,
                'position_id': position_id,
                'repay_amount': repay_amount,
                'withdraw_amount': withdraw_amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ {user} 还款 {repay_amount} {self.symbol}，提取 {withdraw_amount} 抵押品")
            return True

        except Exception as e:
            print(f"❌ 还款提取失败: {e}")
            return False

    def system_health_check(self) -> Dict:
        """系统健康检查"""
        try:
            # 检查各组件状态
            collateral_stats = self.collateral_manager.get_system_stats()
            price_stats = self.price_oracle.get_system_stats()
            liquidation_stats = self.liquidation_system.get_system_stats()
            governance_stats = self.governance_system.get_system_stats()
            stablecoin_stats = self.stablecoin.get_system_stats()

            # 监控清算风险
            liquidation_monitoring = self.liquidation_system.monitor_positions()

            # 计算系统风险指标
            total_collateral_value = Decimal('0')
            total_debt = stablecoin_stats['total_debt']

            for position in self.stablecoin.positions.values():
                price_data = self.price_oracle.get_price(position.collateral_type)
                if price_data:
                    total_collateral_value += position.collateral_amount * price_data.price

            # 计算全局抵押率
            global_collateral_ratio = Decimal('0')
            if total_debt > 0:
                global_collateral_ratio = total_collateral_value / total_debt

            health_status = {
                'system_operational': not self.is_paused and not self.emergency_mode,
                'global_collateral_ratio': global_collateral_ratio,
                'total_collateral_value': total_collateral_value,
                'total_debt': total_debt,
                'liquidation_candidates': liquidation_monitoring['liquidation_candidates'],
                'urgent_liquidations': liquidation_monitoring['urgent_liquidations'],
                'price_feeds_active': price_stats['active_feeds'],
                'governance_active': governance_stats['active_proposals'],
                'system_utilization': total_debt / collateral_stats['system_debt_ceiling']
            }

            # 评估系统健康度
            if global_collateral_ratio < Decimal('1.2'):
                health_status['risk_level'] = 'HIGH'
            elif global_collateral_ratio < Decimal('1.5'):
                health_status['risk_level'] = 'MEDIUM'
            else:
                health_status['risk_level'] = 'LOW'

            return health_status

        except Exception as e:
            print(f"❌ 系统健康检查失败: {e}")
            return {'system_operational': False, 'error': str(e)}

    def emergency_pause(self, admin: str) -> bool:
        """紧急暂停系统"""
        try:
            if admin not in self.admins:
                raise ValueError("无权限执行紧急暂停")

            self.is_paused = True
            self.emergency_mode = True

            # 记录事件
            event = {
                'type': 'emergency_pause',
                'admin': admin,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"🚨 系统已被 {admin} 紧急暂停")
            return True

        except Exception as e:
            print(f"❌ 紧急暂停失败: {e}")
            return False

    def resume_system(self, admin: str) -> bool:
        """恢复系统运行"""
        try:
            if admin not in self.admins:
                raise ValueError("无权限恢复系统")

            self.is_paused = False
            self.emergency_mode = False

            # 记录事件
            event = {
                'type': 'system_resumed',
                'admin': admin,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 系统已被 {admin} 恢复运行")
            return True

        except Exception as e:
            print(f"❌ 恢复系统失败: {e}")
            return False

    def simulate_market_movement(self, price_changes: Dict[str, Decimal]):
        """模拟市场价格变动"""
        print(f"\n📈 模拟市场价格变动...")

        for symbol, change_percent in price_changes.items():
            self.price_oracle.simulate_price_update(symbol, change_percent)

        # 检查是否需要清算
        liquidation_candidates = self.liquidation_system.scan_liquidation_candidates()
        if liquidation_candidates:
            print(f"⚠️ 发现 {len(liquidation_candidates)} 个需要清算的头寸")

            # 自动执行清算
            self.liquidation_system.auto_liquidate()

    def print_full_status(self):
        """打印完整系统状态"""
        print(f"\n{'='*60}")
        print(f"🏦 {self.name} ({self.symbol}) 稳定币系统状态")
        print(f"{'='*60}")
        print(f"版本: {self.version}")
        print(f"创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.created_at))}")
        print(f"系统状态: {'⏸️ 暂停' if self.is_paused else '✅ 运行中'}")
        print(f"紧急模式: {'🚨 是' if self.emergency_mode else '✅ 否'}")

        # 系统健康检查
        health = self.system_health_check()
        print(f"\n🏥 系统健康度: {health.get('risk_level', 'UNKNOWN')}")
        print(f"全局抵押率: {health.get('global_collateral_ratio', 0):.2f}")
        print(f"总抵押品价值: ${health.get('total_collateral_value', 0)}")
        print(f"总债务: {health.get('total_debt', 0)} {self.symbol}")

        # 打印各组件状态
        self.stablecoin.print_status()
        self.collateral_manager.print_status()
        self.price_oracle.print_status()
        self.liquidation_system.print_status()
        self.governance_system.print_status()

        print(f"\n{'='*60}")
        print(f"✅ 系统状态检查完成")
        print(f"{'='*60}")

    def get_user_overview(self, user: str) -> Dict:
        """获取用户概览"""
        overview = {
            'stablecoin_balance': self.stablecoin.balance_of(user),
            'collaterals': self.collateral_manager.get_user_collaterals(user),
            'positions': self.stablecoin.get_user_positions(user),
            'governance_tokens': self.governance_system.get_user_voting_power(user),
            'liquidator_registered': user in self.liquidation_system.liquidators
        }

        return overview
