"""
抵押品管理模块

管理不同类型的抵押品，包括ETH、BTC等加密货币。
"""

import time
from typing import Dict, List, Optional, Set
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum

# 设置精度
getcontext().prec = 50


class CollateralStatus(Enum):
    """抵押品状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LIQUIDATING = "liquidating"
    LIQUIDATED = "liquidated"


@dataclass
class CollateralType:
    """抵押品类型定义"""
    symbol: str
    name: str
    decimals: int
    min_collateral_ratio: Decimal  # 最小抵押率
    liquidation_ratio: Decimal     # 清算阈值
    liquidation_penalty: Decimal   # 清算罚金
    stability_fee: Decimal         # 年化稳定费
    debt_ceiling: Decimal          # 债务上限
    price_feed: str               # 价格数据源
    is_active: bool = True

    def __post_init__(self):
        """初始化后处理"""
        # 确保所有数值都是Decimal类型
        self.min_collateral_ratio = Decimal(str(self.min_collateral_ratio))
        self.liquidation_ratio = Decimal(str(self.liquidation_ratio))
        self.liquidation_penalty = Decimal(str(self.liquidation_penalty))
        self.stability_fee = Decimal(str(self.stability_fee))
        self.debt_ceiling = Decimal(str(self.debt_ceiling))


@dataclass
class CollateralBalance:
    """抵押品余额"""
    user: str
    collateral_type: str
    amount: Decimal
    locked_amount: Decimal = Decimal('0')
    last_updated: float = field(default_factory=time.time)

    def __post_init__(self):
        """初始化后处理"""
        self.amount = Decimal(str(self.amount))
        self.locked_amount = Decimal(str(self.locked_amount))

    @property
    def available_amount(self) -> Decimal:
        """可用余额"""
        return self.amount - self.locked_amount


class CollateralManager:
    """抵押品管理器"""

    def __init__(self):
        # 抵押品类型定义
        self.collateral_types: Dict[str, CollateralType] = {}

        # 抵押品余额 user -> collateral_type -> balance
        self.balances: Dict[str, Dict[str, CollateralBalance]] = {}

        # 抵押品总供应量
        self.total_supply: Dict[str, Decimal] = {}

        # 系统总债务限制
        self.system_debt_ceiling = Decimal('10000000')  # 1000万
        self.current_total_debt = Decimal('0')

        # 事件日志
        self.events: List[Dict] = []

        # 初始化默认抵押品类型
        self._init_default_collaterals()

        print("✅ 抵押品管理器已初始化")

    def _init_default_collaterals(self):
        """初始化默认抵押品类型"""

        # ETH作为抵押品
        eth_collateral = CollateralType(
            symbol="ETH",
            name="Ethereum",
            decimals=18,
            min_collateral_ratio=Decimal('1.5'),    # 150%
            liquidation_ratio=Decimal('1.3'),       # 130%
            liquidation_penalty=Decimal('0.13'),    # 13%
            stability_fee=Decimal('0.02'),          # 2%
            debt_ceiling=Decimal('5000000'),        # 500万
            price_feed="ETH_USD"
        )

        # BTC作为抵押品
        btc_collateral = CollateralType(
            symbol="BTC",
            name="Bitcoin",
            decimals=8,
            min_collateral_ratio=Decimal('1.4'),    # 140%
            liquidation_ratio=Decimal('1.2'),       # 120%
            liquidation_penalty=Decimal('0.10'),    # 10%
            stability_fee=Decimal('0.015'),         # 1.5%
            debt_ceiling=Decimal('3000000'),        # 300万
            price_feed="BTC_USD"
        )

        # USDC作为抵押品（稳定币对稳定币）
        usdc_collateral = CollateralType(
            symbol="USDC",
            name="USD Coin",
            decimals=6,
            min_collateral_ratio=Decimal('1.05'),   # 105%
            liquidation_ratio=Decimal('1.03'),      # 103%
            liquidation_penalty=Decimal('0.03'),    # 3%
            stability_fee=Decimal('0.005'),         # 0.5%
            debt_ceiling=Decimal('2000000'),        # 200万
            price_feed="USDC_USD"
        )

        self.add_collateral_type(eth_collateral)
        self.add_collateral_type(btc_collateral)
        self.add_collateral_type(usdc_collateral)

    def add_collateral_type(self, collateral: CollateralType) -> bool:
        """添加抵押品类型"""
        try:
            if collateral.symbol in self.collateral_types:
                raise ValueError(f"抵押品类型 {collateral.symbol} 已存在")

            self.collateral_types[collateral.symbol] = collateral
            self.total_supply[collateral.symbol] = Decimal('0')

            # 记录事件
            event = {
                'type': 'collateral_type_added',
                'symbol': collateral.symbol,
                'name': collateral.name,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 添加抵押品类型: {collateral.name} ({collateral.symbol})")
            return True

        except Exception as e:
            print(f"❌ 添加抵押品类型失败: {e}")
            return False

    def deposit_collateral(self, user: str, collateral_type: str, amount: Decimal) -> bool:
        """存入抵押品"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("存入数量必须大于0")

            if collateral_type not in self.collateral_types:
                raise ValueError(f"不支持的抵押品类型: {collateral_type}")

            if not self.collateral_types[collateral_type].is_active:
                raise ValueError(f"抵押品类型 {collateral_type} 已停用")

            # 初始化用户余额
            if user not in self.balances:
                self.balances[user] = {}

            if collateral_type not in self.balances[user]:
                self.balances[user][collateral_type] = CollateralBalance(
                    user=user,
                    collateral_type=collateral_type,
                    amount=Decimal('0')
                )

            # 更新余额
            self.balances[user][collateral_type].amount += amount
            self.balances[user][collateral_type].last_updated = time.time()

            # 更新总供应量
            self.total_supply[collateral_type] += amount

            # 记录事件
            event = {
                'type': 'collateral_deposit',
                'user': user,
                'collateral_type': collateral_type,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ {user} 存入 {amount} {collateral_type}")
            return True

        except Exception as e:
            print(f"❌ 存入抵押品失败: {e}")
            return False

    def withdraw_collateral(self, user: str, collateral_type: str, amount: Decimal) -> bool:
        """提取抵押品"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("提取数量必须大于0")

            if user not in self.balances or collateral_type not in self.balances[user]:
                raise ValueError("抵押品余额不足")

            balance = self.balances[user][collateral_type]
            if balance.available_amount < amount:
                raise ValueError(f"可用余额不足，可用: {balance.available_amount}")

            # 更新余额
            balance.amount -= amount
            balance.last_updated = time.time()

            # 更新总供应量
            self.total_supply[collateral_type] -= amount

            # 记录事件
            event = {
                'type': 'collateral_withdrawal',
                'user': user,
                'collateral_type': collateral_type,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ {user} 提取 {amount} {collateral_type}")
            return True

        except Exception as e:
            print(f"❌ 提取抵押品失败: {e}")
            return False

    def lock_collateral(self, user: str, collateral_type: str, amount: Decimal) -> bool:
        """锁定抵押品（用于借贷）"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("锁定数量必须大于0")

            if user not in self.balances or collateral_type not in self.balances[user]:
                raise ValueError("抵押品余额不足")

            balance = self.balances[user][collateral_type]
            if balance.available_amount < amount:
                raise ValueError(f"可用余额不足，可用: {balance.available_amount}")

            # 锁定抵押品
            balance.locked_amount += amount
            balance.last_updated = time.time()

            # 记录事件
            event = {
                'type': 'collateral_locked',
                'user': user,
                'collateral_type': collateral_type,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 锁定 {user} 的 {amount} {collateral_type}")
            return True

        except Exception as e:
            print(f"❌ 锁定抵押品失败: {e}")
            return False

    def unlock_collateral(self, user: str, collateral_type: str, amount: Decimal) -> bool:
        """解锁抵押品"""
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError("解锁数量必须大于0")

            if user not in self.balances or collateral_type not in self.balances[user]:
                raise ValueError("抵押品余额不足")

            balance = self.balances[user][collateral_type]
            if balance.locked_amount < amount:
                raise ValueError(f"锁定余额不足，锁定: {balance.locked_amount}")

            # 解锁抵押品
            balance.locked_amount -= amount
            balance.last_updated = time.time()

            # 记录事件
            event = {
                'type': 'collateral_unlocked',
                'user': user,
                'collateral_type': collateral_type,
                'amount': amount,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 解锁 {user} 的 {amount} {collateral_type}")
            return True

        except Exception as e:
            print(f"❌ 解锁抵押品失败: {e}")
            return False

    def get_collateral_balance(
            self,
            user: str,
            collateral_type: str) -> Optional[CollateralBalance]:
        """获取抵押品余额"""
        if user not in self.balances or collateral_type not in self.balances[user]:
            return None
        return self.balances[user][collateral_type]

    def get_user_collaterals(self, user: str) -> Dict[str, CollateralBalance]:
        """获取用户所有抵押品"""
        if user not in self.balances:
            return {}
        return self.balances[user].copy()

    def get_collateral_type(self, symbol: str) -> Optional[CollateralType]:
        """获取抵押品类型信息"""
        return self.collateral_types.get(symbol)

    def get_all_collateral_types(self) -> Dict[str, CollateralType]:
        """获取所有抵押品类型"""
        return self.collateral_types.copy()

    def get_total_supply(self, collateral_type: str) -> Decimal:
        """获取抵押品总供应量"""
        return self.total_supply.get(collateral_type, Decimal('0'))

    def calculate_collateral_value(
            self,
            collateral_type: str,
            amount: Decimal,
            price: Decimal) -> Decimal:
        """计算抵押品价值"""
        return Decimal(str(amount)) * Decimal(str(price))

    def check_debt_ceiling(self, collateral_type: str, additional_debt: Decimal) -> bool:
        """检查债务上限"""
        if collateral_type not in self.collateral_types:
            return False

        collateral = self.collateral_types[collateral_type]
        current_debt = self.get_collateral_debt(collateral_type)

        return current_debt + Decimal(str(additional_debt)) <= collateral.debt_ceiling

    def get_collateral_debt(self, collateral_type: str) -> Decimal:
        """获取特定抵押品的总债务（需要从稳定币合约获取）"""
        # 这里应该与稳定币合约交互获取实际债务
        # 暂时返回0，实际使用时需要实现
        return Decimal('0')

    def update_collateral_type(self, symbol: str, **kwargs) -> bool:
        """更新抵押品类型参数"""
        try:
            if symbol not in self.collateral_types:
                raise ValueError(f"抵押品类型 {symbol} 不存在")

            collateral = self.collateral_types[symbol]

            # 更新参数
            for key, value in kwargs.items():
                if hasattr(collateral, key):
                    if key in ['min_collateral_ratio', 'liquidation_ratio',
                               'liquidation_penalty', 'stability_fee', 'debt_ceiling']:
                        setattr(collateral, key, Decimal(str(value)))
                    else:
                        setattr(collateral, key, value)

            # 记录事件
            event = {
                'type': 'collateral_type_updated',
                'symbol': symbol,
                'updates': kwargs,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ 更新抵押品类型 {symbol} 参数")
            return True

        except Exception as e:
            print(f"❌ 更新抵押品类型失败: {e}")
            return False

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        stats = {
            'total_collateral_types': len(self.collateral_types),
            'system_debt_ceiling': self.system_debt_ceiling,
            'current_total_debt': self.current_total_debt,
            'collateral_supplies': self.total_supply.copy(),
            'active_collaterals': len([c for c in self.collateral_types.values() if c.is_active])
        }
        return stats

    def print_status(self):
        """打印系统状态"""
        stats = self.get_system_stats()
        print(f"\n=== 抵押品管理系统状态 ===")
        print(f"抵押品类型数量: {stats['total_collateral_types']}")
        print(f"活跃抵押品数量: {stats['active_collaterals']}")
        print(f"系统债务上限: {stats['system_debt_ceiling']}")
        print(f"当前总债务: {stats['current_total_debt']}")

        print(f"\n--- 抵押品类型详情 ---")
        for symbol, collateral in self.collateral_types.items():
            print(f"{symbol} ({collateral.name}):")
            print(f"  状态: {'活跃' if collateral.is_active else '停用'}")
            print(f"  最小抵押率: {collateral.min_collateral_ratio}%")
            print(f"  清算阈值: {collateral.liquidation_ratio}%")
            print(f"  总供应量: {self.total_supply[symbol]}")
            print(f"  债务上限: {collateral.debt_ceiling}")
