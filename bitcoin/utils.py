#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 工具类模块
包含比特币系统中使用的各种工具函数
"""

import json
import hashlib
from typing import Dict, Any, Union


class HashUtils:
    """统一的哈希计算工具类"""

    @staticmethod
    def calculate_sha256(data: Union[str, Dict[str, Any]]) -> str:
        """
        计算SHA256哈希值
        Args:
            data: 要计算哈希的数据（字符串或字典）
        Returns:
            str: 十六进制哈希值
        """
        if isinstance(data, dict):
            data_string = json.dumps(data, sort_keys=True)
        else:
            data_string = data

        return hashlib.sha256(data_string.encode()).hexdigest()

    @staticmethod
    def calculate_block_hash(index: int, merkle_root: str, previous_hash: str,
                             timestamp: str, nonce: int) -> str:
        """
        计算区块哈希值
        Args:
            index: 区块索引
            merkle_root: Merkle根
            previous_hash: 前一个区块哈希
            timestamp: 时间戳
            nonce: 随机数
        Returns:
            str: 区块哈希值
        """
        block_data = {
            "index": index,
            "merkle_root": merkle_root,
            "previous_hash": previous_hash,
            "timestamp": timestamp,
            "nonce": nonce
        }
        return HashUtils.calculate_sha256(block_data)

    @staticmethod
    def calculate_transaction_hash(transaction_data: str) -> str:
        """
        计算交易哈希值
        Args:
            transaction_data: 交易数据字符串
        Returns:
            str: 交易哈希值
        """
        return HashUtils.calculate_sha256(transaction_data)


class ValidationUtils:
    """验证工具类"""

    @staticmethod
    def is_valid_hash(hash_string: str) -> bool:
        """
        验证哈希字符串是否有效
        Args:
            hash_string: 哈希字符串
        Returns:
            bool: 是否有效
        """
        if not hash_string or len(hash_string) != 64:
            return False

        try:
            int(hash_string, 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_address(address: str) -> bool:
        """
        验证地址格式是否有效
        Args:
            address: 地址字符串
        Returns:
            bool: 是否有效
        """
        return bool(address and len(address) > 0)


class CacheUtils:
    """缓存工具类"""

    @staticmethod
    def generate_cache_key(*args) -> str:
        """
        生成缓存键
        Args:
            *args: 用于生成键的参数
        Returns:
            str: 缓存键
        """
        key_data = str(args)
        return hashlib.md5(key_data.encode()).hexdigest()
