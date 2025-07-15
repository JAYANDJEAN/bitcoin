"""
价格预言机模块

提供可靠的资产价格数据，支持多种数据源和价格聚合。
"""

import time
import random
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum

# 设置精度
getcontext().prec = 50


class PriceStatus(Enum):
    """价格状态"""
    ACTIVE = "active"
    STALE = "stale"
    INVALID = "invalid"


@dataclass
class PriceData:
    """价格数据结构"""
    symbol: str
    price: Decimal
    timestamp: float
    source: str
    confidence: Decimal = Decimal('1.0')  # 置信度 0-1
    status: PriceStatus = PriceStatus.ACTIVE

    def __post_init__(self):
        """初始化后处理"""
        self.price = Decimal(str(self.price))
        self.confidence = Decimal(str(self.confidence))

    @property
    def age(self) -> float:
        """价格数据的年龄（秒）"""
        return time.time() - self.timestamp

    def is_fresh(self, max_age: float = 300) -> bool:
        """检查价格是否新鲜（默认5分钟内）"""
        return self.age <= max_age

    def is_valid(self) -> bool:
        """检查价格是否有效"""
        return (self.status == PriceStatus.ACTIVE and
                self.price > 0 and
                self.confidence > Decimal('0.5'))


@dataclass
class PriceFeed:
    """价格数据源配置"""
    symbol: str
    source_name: str
    update_interval: float  # 更新间隔（秒）
    max_deviation: Decimal  # 最大允许偏差
    weight: Decimal = Decimal('1.0')  # 权重
    is_active: bool = True
    last_update: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        self.max_deviation = Decimal(str(self.max_deviation))
        self.weight = Decimal(str(self.weight))


class PriceOracle:
    """价格预言机"""

    def __init__(self):
        # 价格数据存储 symbol -> source -> PriceData
        self.prices: Dict[str, Dict[str, PriceData]] = {}

        # 聚合价格 symbol -> PriceData
        self.aggregated_prices: Dict[str, PriceData] = {}

        # 价格历史 symbol -> List[PriceData]
        self.price_history: Dict[str, List[PriceData]] = {}

        # 数据源配置
        self.price_feeds: Dict[str, List[PriceFeed]] = {}

        # 系统参数
        self.max_price_age = 300  # 最大价格年龄（秒）
        self.min_sources = 2      # 最少数据源数量
        self.price_deviation_threshold = Decimal('0.05')  # 5%偏差阈值

        # 事件日志
        self.events: List[Dict] = []

        # 初始化默认价格数据源
        self._init_default_feeds()

        # 初始化模拟价格
        self._init_mock_prices()

        print("✅ 价格预言机已初始化")

    def _init_default_feeds(self):
        """初始化默认价格数据源"""

        # ETH价格数据源
        eth_feeds = [
            PriceFeed("ETH", "Coinbase", 30, Decimal('0.02')),
            PriceFeed("ETH", "Binance", 30, Decimal('0.02')),
            PriceFeed("ETH", "Kraken", 60, Decimal('0.03'))
        ]

        # BTC价格数据源
        btc_feeds = [
            PriceFeed("BTC", "Coinbase", 30, Decimal('0.02')),
            PriceFeed("BTC", "Binance", 30, Decimal('0.02')),
            PriceFeed("BTC", "Kraken", 60, Decimal('0.03'))
        ]

        # USDC价格数据源
        usdc_feeds = [
            PriceFeed("USDC", "Coinbase", 60, Decimal('0.005')),
            PriceFeed("USDC", "Binance", 60, Decimal('0.005'))
        ]

        self.price_feeds["ETH"] = eth_feeds
        self.price_feeds["BTC"] = btc_feeds
        self.price_feeds["USDC"] = usdc_feeds

    def _init_mock_prices(self):
        """初始化模拟价格数据"""
        # 模拟当前市场价格
        mock_prices = {
            "ETH": Decimal('2000.00'),
            "BTC": Decimal('45000.00'),
            "USDC": Decimal('1.00')
        }

        current_time = time.time()

        for symbol, base_price in mock_prices.items():
            if symbol not in self.prices:
                self.prices[symbol] = {}
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            # 为每个数据源生成略有差异的价格
            for feed in self.price_feeds.get(symbol, []):
                # 添加小幅随机波动（±1%）
                variation = Decimal(str(random.uniform(-0.01, 0.01)))
                price = base_price * (Decimal('1') + variation)

                price_data = PriceData(
                    symbol=symbol,
                    price=price,
                    timestamp=current_time,
                    source=feed.source_name,
                    confidence=Decimal('0.95')
                )

                self.prices[symbol][feed.source_name] = price_data

            # 计算聚合价格
            self._aggregate_price(symbol)

    def add_price_feed(self, feed: PriceFeed) -> bool:
        """添加价格数据源"""
        try:
            if feed.symbol not in self.price_feeds:
                self.price_feeds[feed.symbol] = []

            # 检查是否已存在相同的数据源
            existing_sources = [f.source_name for f in self.price_feeds[feed.symbol]]
            if feed.source_name in existing_sources:
                raise ValueError(f"数据源 {feed.source_name} 已存在")

            self.price_feeds[feed.symbol].append(feed)

            print(f"✅ 添加价格数据源: {feed.symbol} - {feed.source_name}")
            return True

        except Exception as e:
            print(f"❌ 添加价格数据源失败: {e}")
            return False

    def update_price(self, symbol: str, source: str, price: Decimal,
                     confidence: Decimal = Decimal('1.0')) -> bool:
        """更新价格数据"""
        try:
            price = Decimal(str(price))
            confidence = Decimal(str(confidence))

            if price <= 0:
                raise ValueError("价格必须大于0")

            if confidence < 0 or confidence > 1:
                raise ValueError("置信度必须在0-1之间")

            # 创建价格数据
            price_data = PriceData(
                symbol=symbol,
                price=price,
                timestamp=time.time(),
                source=source,
                confidence=confidence
            )

            # 存储价格数据
            if symbol not in self.prices:
                self.prices[symbol] = {}

            self.prices[symbol][source] = price_data

            # 添加到历史记录
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            self.price_history[symbol].append(price_data)

            # 限制历史记录长度
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]

            # 重新计算聚合价格
            self._aggregate_price(symbol)

            # 记录事件
            event = {
                'type': 'price_updated',
                'symbol': symbol,
                'source': source,
                'price': price,
                'timestamp': time.time()
            }
            self.events.append(event)

            return True

        except Exception as e:
            print(f"❌ 更新价格失败: {e}")
            return False

    def _aggregate_price(self, symbol: str) -> bool:
        """聚合多个数据源的价格"""
        try:
            if symbol not in self.prices or not self.prices[symbol]:
                return False

            valid_prices = []
            total_weight = Decimal('0')

            # 收集有效的价格数据
            for source, price_data in self.prices[symbol].items():
                if price_data.is_valid() and price_data.is_fresh(self.max_price_age):
                    # 获取数据源权重
                    weight = self._get_source_weight(symbol, source)
                    valid_prices.append((price_data.price, weight, price_data.confidence))
                    total_weight += weight

            if len(valid_prices) < self.min_sources:
                print(f"⚠️ {symbol} 有效数据源不足")
                return False

            # 加权平均计算
            weighted_sum = Decimal('0')
            confidence_sum = Decimal('0')

            for price, weight, confidence in valid_prices:
                normalized_weight = weight / total_weight
                weighted_sum += price * normalized_weight
                confidence_sum += confidence * normalized_weight

            # 创建聚合价格数据
            aggregated_price = PriceData(
                symbol=symbol,
                price=weighted_sum,
                timestamp=time.time(),
                source="aggregated",
                confidence=confidence_sum
            )

            self.aggregated_prices[symbol] = aggregated_price

            return True

        except Exception as e:
            print(f"❌ 聚合价格失败: {e}")
            return False

    def _get_source_weight(self, symbol: str, source: str) -> Decimal:
        """获取数据源权重"""
        if symbol not in self.price_feeds:
            return Decimal('1.0')

        for feed in self.price_feeds[symbol]:
            if feed.source_name == source and feed.is_active:
                return feed.weight

        return Decimal('1.0')

    def get_price(self, symbol: str) -> Optional[PriceData]:
        """获取聚合价格"""
        if symbol not in self.aggregated_prices:
            return None

        price_data = self.aggregated_prices[symbol]

        # 检查价格是否新鲜
        if not price_data.is_fresh(self.max_price_age):
            print(f"⚠️ {symbol} 价格数据过时")
            return None

        return price_data

    def get_raw_prices(self, symbol: str) -> Dict[str, PriceData]:
        """获取所有原始价格数据"""
        return self.prices.get(symbol, {}).copy()

    def get_price_history(self, symbol: str, limit: int = 100) -> List[PriceData]:
        """获取价格历史"""
        if symbol not in self.price_history:
            return []

        return self.price_history[symbol][-limit:]

    def simulate_price_update(self, symbol: str, volatility: Decimal = Decimal('0.02')):
        """模拟价格更新（用于测试）"""
        if symbol not in self.aggregated_prices:
            print(f"❌ 未找到 {symbol} 的价格数据")
            return

        current_price = self.aggregated_prices[symbol].price

        # 为每个数据源生成新价格
        for source in self.prices.get(symbol, {}):
            # 生成随机价格变动
            change = Decimal(str(random.uniform(-float(volatility), float(volatility))))
            new_price = current_price * (Decimal('1') + change)

            # 更新价格
            self.update_price(symbol, source, new_price)

        print(f"✅ 模拟更新 {symbol} 价格")

    def check_price_deviation(self, symbol: str) -> bool:
        """检查价格偏差是否过大"""
        if symbol not in self.prices or len(self.prices[symbol]) < 2:
            return True

        prices = [p.price for p in self.prices[symbol].values() if p.is_valid()]
        if len(prices) < 2:
            return True

        min_price = min(prices)
        max_price = max(prices)

        if min_price > 0:
            deviation = (max_price - min_price) / min_price
            return deviation <= self.price_deviation_threshold

        return True

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        total_feeds = sum(len(feeds) for feeds in self.price_feeds.values())
        active_feeds = sum(len([f for f in feeds if f.is_active])
                           for feeds in self.price_feeds.values())

        return {
            'total_symbols': len(self.price_feeds),
            'total_feeds': total_feeds,
            'active_feeds': active_feeds,
            'aggregated_prices': len(self.aggregated_prices),
            'max_price_age': self.max_price_age,
            'min_sources': self.min_sources,
            'price_deviation_threshold': self.price_deviation_threshold
        }

    def print_status(self):
        """打印系统状态"""
        stats = self.get_system_stats()
        print(f"\n=== 价格预言机状态 ===")
        print(f"支持资产数量: {stats['total_symbols']}")
        print(f"数据源总数: {stats['total_feeds']}")
        print(f"活跃数据源: {stats['active_feeds']}")
        print(f"聚合价格数量: {stats['aggregated_prices']}")
        print(f"最大价格年龄: {stats['max_price_age']}秒")

        print(f"\n--- 当前价格 ---")
        for symbol, price_data in self.aggregated_prices.items():
            print(f"{symbol}: ${price_data.price} (置信度: {price_data.confidence:.2f})")
