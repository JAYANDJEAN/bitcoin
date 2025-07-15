"""
稳定币系统 - 完整的去中心化稳定币实现

本模块实现了一个完整的稳定币系统，包括：
- 稳定币代币合约
- 抵押品管理系统
- 价格预言机
- 清算机制
- 治理系统

支持多种抵押品类型和灵活的风险管理参数。
"""

from .stablecoin_core import StableCoin, StableCoinPosition
from .collateral_manager import CollateralManager, CollateralType
from .price_oracle import PriceOracle, PriceData
from .liquidation_system import LiquidationSystem, LiquidationEvent
from .governance import GovernanceSystem, Proposal, Vote
from .stablecoin_factory import StableCoinFactory

__version__ = "1.0.0"
__author__ = "AI Assistant"

__all__ = [
    "StableCoin",
    "StableCoinPosition",
    "CollateralManager",
    "CollateralType",
    "PriceOracle",
    "PriceData",
    "LiquidationSystem",
    "LiquidationEvent",
    "GovernanceSystem",
    "Proposal",
    "Vote",
    "StableCoinFactory"
]
