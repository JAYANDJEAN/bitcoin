"""
稳定币核心模块

实现稳定币代币合约和头寸管理系统。
"""

import hashlib
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, getcontext
from dataclasses import dataclass, field

# 设置精度
getcontext().prec = 50


@dataclass
class StableCoinPosition:
    """稳定币头寸数据结构"""
    position_id: str
    owner: str
    collateral_type: str
    collateral_amount: Decimal
    debt_amount: Decimal  # 借出的稳定币数量
    created_at: float
    last_updated: float
    liquidation_price: Decimal = Decimal('0')
    collateral_ratio: Decimal = Decimal('0')

    def __post_init__(self):
        """初始化后处理"""
        if not self.position_id:
            self.position_id = self._generate_position_id()

    def _generate_position_id(self) -> str:
        """生成唯一的头寸ID"""
        data = f"{self.owner}{self.collateral_type}{self.created_at}{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def update_ratios(self, collateral_price: Decimal):
        """更新抵押率和清算价格"""
        if self.debt_amount > 0:
            collateral_value = self.collateral_amount * collateral_price
            self.collateral_ratio = collateral_value / self.debt_amount
            # 假设清算阈值为150%
            self.liquidation_price = (self.debt_amount * Decimal('1.5')) / self.collateral_amount
        else:
            self.collateral_ratio = Decimal('0')
            self.liquidation_price = Decimal('0')

        self.last_updated = time.time()


class StableCoin:
    """稳定币主合约"""

    def __init__(self, name: str = "DecentralizedUSD", symbol: str = "DUSD"):
        self.name = name
        self.symbol = symbol
        self.decimals = 18
        self.total_supply = Decimal('0')

        # 余额映射
        self.balances: Dict[str, Decimal] = {}

        # 授权映射 owner -> spender -> amount
        self.allowances: Dict[str, Dict[str, Decimal]] = {}

        # 头寸映射
        self.positions: Dict[str, StableCoinPosition] = {}
        self.user_positions: Dict[str, List[str]] = {}  # 用户 -> 头寸ID列表

        # 系统参数
        self.min_collateral_ratio = Decimal('1.5')  # 最小抵押率150%
        self.liquidation_ratio = Decimal('1.3')     # 清算阈值130%
        self.stability_fee = Decimal('0.02')        # 年化稳定费2%

        # 事件日志
        self.events: List[Dict] = []

        print(f"✅ 稳定币 {self.name} ({self.symbol}) 已创建")

    def mint(self, to: str, amount: Decimal, position_id: str = None) -> bool:
        """铸造稳定币"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("铸造数量必须大于0")

            # 更新余额
            if to not in self.balances:
                self.balances[to] = Decimal('0')

            self.balances[to] += amount
            self.total_supply += amount

            # 记录事件
            event = {
                'type': 'mint',
                'to': to,
                'amount': amount,
                'position_id': position_id,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 为 {to} 铸造了 {amount} {self.symbol}")
            return True

        except Exception as e:
            print(f"❌ 铸造失败: {e}")
            return False

    def burn(self, from_addr: str, amount: Decimal) -> bool:
        """销毁稳定币"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("销毁数量必须大于0")

            if from_addr not in self.balances:
                raise ValueError("账户不存在")

            if self.balances[from_addr] < amount:
                raise ValueError("余额不足")

            # 更新余额
            self.balances[from_addr] -= amount
            self.total_supply -= amount

            # 记录事件
            event = {
                'type': 'burn',
                'from': from_addr,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 从 {from_addr} 销毁了 {amount} {self.symbol}")
            return True

        except Exception as e:
            print(f"❌ 销毁失败: {e}")
            return False

    def transfer(self, from_addr: str, to: str, amount: Decimal) -> bool:
        """转账稳定币"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("转账数量必须大于0")

            if from_addr not in self.balances:
                raise ValueError("发送方账户不存在")

            if self.balances[from_addr] < amount:
                raise ValueError("余额不足")

            # 更新余额
            self.balances[from_addr] -= amount

            if to not in self.balances:
                self.balances[to] = Decimal('0')
            self.balances[to] += amount

            # 记录事件
            event = {
                'type': 'transfer',
                'from': from_addr,
                'to': to,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 从 {from_addr} 向 {to} 转账 {amount} {self.symbol}")
            return True

        except Exception as e:
            print(f"❌ 转账失败: {e}")
            return False

    def approve(self, owner: str, spender: str, amount: Decimal) -> bool:
        """授权转账"""
        try:
            amount = Decimal(str(amount))

            if owner not in self.allowances:
                self.allowances[owner] = {}

            self.allowances[owner][spender] = amount

            # 记录事件
            event = {
                'type': 'approval',
                'owner': owner,
                'spender': spender,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ {owner} 授权 {spender} 使用 {amount} {self.symbol}")
            return True

        except Exception as e:
            print(f"❌ 授权失败: {e}")
            return False

    def transfer_from(self, spender: str, from_addr: str, to: str, amount: Decimal) -> bool:
        """代理转账"""
        try:
            amount = Decimal(str(amount))

            # 检查授权
            if (from_addr not in self.allowances or
                spender not in self.allowances[from_addr] or
                    self.allowances[from_addr][spender] < amount):
                raise ValueError("授权额度不足")

            # 执行转账
            if not self.transfer(from_addr, to, amount):
                return False

            # 减少授权额度
            self.allowances[from_addr][spender] -= amount

            print(f"✅ {spender} 代理转账成功")
            return True

        except Exception as e:
            print(f"❌ 代理转账失败: {e}")
            return False

    def create_position(self, owner: str, collateral_type: str,
                        collateral_amount: Decimal, debt_amount: Decimal) -> str:
        """创建新头寸"""
        try:
            position = StableCoinPosition(
                position_id="",
                owner=owner,
                collateral_type=collateral_type,
                collateral_amount=Decimal(str(collateral_amount)),
                debt_amount=Decimal(str(debt_amount)),
                created_at=time.time(),
                last_updated=time.time()
            )

            # 存储头寸
            self.positions[position.position_id] = position

            if owner not in self.user_positions:
                self.user_positions[owner] = []
            self.user_positions[owner].append(position.position_id)

            print(f"✅ 创建头寸 {position.position_id} 成功")
            return position.position_id

        except Exception as e:
            print(f"❌ 创建头寸失败: {e}")
            return ""

    def get_position(self, position_id: str) -> Optional[StableCoinPosition]:
        """获取头寸信息"""
        return self.positions.get(position_id)

    def get_user_positions(self, user: str) -> List[StableCoinPosition]:
        """获取用户所有头寸"""
        if user not in self.user_positions:
            return []

        positions = []
        for position_id in self.user_positions[user]:
            if position_id in self.positions:
                positions.append(self.positions[position_id])

        return positions

    def balance_of(self, account: str) -> Decimal:
        """查询余额"""
        return self.balances.get(account, Decimal('0'))

    def allowance(self, owner: str, spender: str) -> Decimal:
        """查询授权额度"""
        if owner not in self.allowances:
            return Decimal('0')
        return self.allowances[owner].get(spender, Decimal('0'))

    def get_total_supply(self) -> Decimal:
        """获取总供应量"""
        return self.total_supply

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        total_positions = len(self.positions)
        total_debt = sum(pos.debt_amount for pos in self.positions.values())

        return {
            'name': self.name,
            'symbol': self.symbol,
            'total_supply': self.total_supply,
            'total_positions': total_positions,
            'total_debt': total_debt,
            'min_collateral_ratio': self.min_collateral_ratio,
            'liquidation_ratio': self.liquidation_ratio,
            'stability_fee': self.stability_fee
        }

    def print_status(self):
        """打印系统状态"""
        stats = self.get_system_stats()
        print(f"\n=== {self.name} 系统状态 ===")
        print(f"代币符号: {stats['symbol']}")
        print(f"总供应量: {stats['total_supply']}")
        print(f"总头寸数: {stats['total_positions']}")
        print(f"总债务: {stats['total_debt']}")
        print(f"最小抵押率: {stats['min_collateral_ratio']}%")
        print(f"清算阈值: {stats['liquidation_ratio']}%")
        print(f"稳定费: {stats['stability_fee']}%")
