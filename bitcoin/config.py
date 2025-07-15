#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ 配置管理模块
统一管理比特币系统的所有配置参数
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class NetworkConfig:
    """网络配置"""
    delay: float = 0.1  # 网络延迟模拟(秒)
    timeout: int = 30000  # API超时时间(毫秒)
    max_connections: int = 8  # 最大连接数


@dataclass
class MiningConfig:
    """挖矿配置"""
    default_difficulty: int = 4  # 默认挖矿难度
    default_reward: float = 50.0  # 默认挖矿奖励
    max_nonce: int = 2**32  # 最大nonce值
    progress_interval: int = 5000  # 进度报告间隔


@dataclass
class TransactionConfig:
    """交易配置"""
    default_fee: float = 0.01  # 默认交易手续费
    max_inputs: int = 100  # 最大输入数量
    max_outputs: int = 100  # 最大输出数量
    confirmation_blocks: int = 6  # 确认所需区块数


@dataclass
class SecurityConfig:
    """安全配置"""
    address_version: bytes = b'\x00'  # 比特币主网地址版本
    private_key_version: bytes = b'\x80'  # 私钥WIF版本
    key_length: int = 32  # 密钥长度(字节)
    hash_length: int = 64  # 哈希长度(字符)


@dataclass
class DisplayConfig:
    """显示配置"""
    hash_display_length: int = 16  # 哈希显示长度
    max_log_entries: int = 100  # 最大日志条目数
    refresh_interval: int = 5000  # 刷新间隔(毫秒)
    animation_duration: int = 300  # 动画持续时间(毫秒)


@dataclass
class CacheConfig:
    """缓存配置"""
    enable_cache: bool = True  # 启用缓存
    max_cache_size: int = 1000  # 最大缓存大小
    cache_ttl: int = 3600  # 缓存生存时间(秒)
    history_cache_size: int = 500  # 历史缓存大小


@dataclass
class DatabaseConfig:
    """数据库配置"""
    max_block_size: int = 1048576  # 最大区块大小(字节)
    max_chain_length: int = 1000000  # 最大链长度
    backup_interval: int = 3600  # 备份间隔(秒)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        Args:
            config_file: 配置文件路径（可选）
        """
        self.network = NetworkConfig()
        self.mining = MiningConfig()
        self.transaction = TransactionConfig()
        self.security = SecurityConfig()
        self.display = DisplayConfig()
        self.cache = CacheConfig()
        self.database = DatabaseConfig()

        # 从环境变量加载配置
        self._load_from_env()

        # 从文件加载配置
        if config_file:
            self._load_from_file(config_file)

    def _load_from_env(self):
        """从环境变量加载配置"""
        # 挖矿配置
        if os.getenv('BITCOIN_DIFFICULTY'):
            self.mining.default_difficulty = int(os.getenv('BITCOIN_DIFFICULTY'))
        if os.getenv('BITCOIN_REWARD'):
            self.mining.default_reward = float(os.getenv('BITCOIN_REWARD'))

        # 交易配置
        if os.getenv('BITCOIN_TX_FEE'):
            self.transaction.default_fee = float(os.getenv('BITCOIN_TX_FEE'))

        # 网络配置
        if os.getenv('BITCOIN_NETWORK_TIMEOUT'):
            self.network.timeout = int(os.getenv('BITCOIN_NETWORK_TIMEOUT'))

        # 缓存配置
        if os.getenv('BITCOIN_CACHE_ENABLED'):
            self.cache.enable_cache = os.getenv('BITCOIN_CACHE_ENABLED').lower() == 'true'

    def _load_from_file(self, config_file: str):
        """从文件加载配置"""
        try:
            import json
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # 更新配置
            for section, values in config_data.items():
                if hasattr(self, section):
                    section_config = getattr(self, section)
                    for key, value in values.items():
                        if hasattr(section_config, key):
                            setattr(section_config, key, value)
        except Exception as e:
            print(f"警告: 无法加载配置文件 {config_file}: {e}")

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            'network': self.network.__dict__,
            'mining': self.mining.__dict__,
            'transaction': self.transaction.__dict__,
            'security': self.security.__dict__,
            'display': self.display.__dict__,
            'cache': self.cache.__dict__,
            'database': self.database.__dict__
        }

    def get_frontend_config(self) -> Dict[str, Any]:
        """获取前端配置"""
        return {
            'refreshInterval': self.display.refresh_interval,
            'apiTimeout': self.network.timeout,
            'maxLogEntries': self.display.max_log_entries,
            'animationDuration': self.display.animation_duration
        }

    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证挖矿配置
            assert self.mining.default_difficulty > 0, "挖矿难度必须大于0"
            assert self.mining.default_reward > 0, "挖矿奖励必须大于0"

            # 验证交易配置
            assert self.transaction.default_fee >= 0, "交易手续费不能为负数"

            # 验证网络配置
            assert self.network.timeout > 0, "网络超时时间必须大于0"

            # 验证显示配置
            assert self.display.hash_display_length > 0, "哈希显示长度必须大于0"

            return True
        except AssertionError as e:
            print(f"配置验证失败: {e}")
            return False


# 全局配置实例
config = ConfigManager()


# 向后兼容的常量（保持与现有代码的兼容性）
DEFAULT_DIFFICULTY = config.mining.default_difficulty
DEFAULT_MINING_REWARD = config.mining.default_reward
DEFAULT_TRANSACTION_FEE = config.transaction.default_fee
BITCOIN_ADDRESS_VERSION = config.security.address_version
PRIVATE_KEY_VERSION = config.security.private_key_version
NETWORK_DELAY = config.network.delay
HASH_DISPLAY_LENGTH = config.display.hash_display_length
