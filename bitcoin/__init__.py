#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 Bitcoin模块 - 完整的比特币区块链实现

这是一个教育用途的比特币区块链模拟器，实现了比特币的核心功能：
- 钱包系统（ECDSA/SECP256k1密钥对）
- 数字签名交易
- 工作量证明挖矿
- UTXO模型
- 区块链数据结构
- Merkle树验证
- P2P网络模拟
- 动态难度调整
"""

import os

# 导入常量
from .config import (
    BITCOIN_ADDRESS_VERSION,
    PRIVATE_KEY_VERSION,
    DEFAULT_DIFFICULTY,
    DEFAULT_MINING_REWARD,
    DEFAULT_TRANSACTION_FEE,
    NETWORK_DELAY,
    HASH_DISPLAY_LENGTH
)

# 版本信息
__version__ = "1.0.1"
__author__ = "AI Assistant"

# 导入钱包相关类
from .wallet import (
    Wallet,
    WalletManager
)

# 导入交易相关类
from .transaction import (
    UTXO,
    TransactionInput,
    TransactionOutput,
    Transaction,
    UTXOSet,
    AddressValidator
)

# 导入区块链相关类（包含Block和Blockchain）
from .blockchain import Block, Blockchain, UTXOFilter, TransactionHistoryCache, BlockchainDisplay

# 导入Merkle树实现
from .merkle_tree import MerkleTree, MerkleProof, SPVClient

# 导入网络相关类 (暂时注释掉，因为当前未使用)
# from .network import (
#     NetworkNode,
#     DistributedNetwork
# )

# 导入难度调整相关类
from .difficulty_adjustment import (
    DifficultyAdjustment,
    BlockHeader
)

# 定义核心API
__all__ = [
    # 常量
    'BITCOIN_ADDRESS_VERSION',
    'PRIVATE_KEY_VERSION',
    'DEFAULT_DIFFICULTY',
    'DEFAULT_MINING_REWARD',
    'DEFAULT_TRANSACTION_FEE',
    'NETWORK_DELAY',
    'HASH_DISPLAY_LENGTH',
    '__version__',
    '__author__',

    # 核心类
    'Wallet',
    'WalletManager',
    'UTXO',
    'TransactionInput',
    'TransactionOutput',
    'Transaction',
    'UTXOSet',
    'AddressValidator',
    'Block',
    'Blockchain',
    'UTXOFilter',
    'TransactionHistoryCache',
    'BlockchainDisplay',

    # Merkle树相关
    'MerkleTree',
    'MerkleProof',
    'SPVClient',

    # 网络相关 (暂时注释掉，因为当前未使用)
    # 'NetworkNode',
    # 'DistributedNetwork',

    # 难度调整相关
    'DifficultyAdjustment',
    'BlockHeader',
]

# 便捷函数


def create_wallet(private_key=None):
    """便捷函数：创建钱包"""
    return Wallet(private_key)


def create_blockchain(difficulty=DEFAULT_DIFFICULTY, mining_reward=DEFAULT_MINING_REWARD):
    """便捷函数：创建区块链"""
    return Blockchain(difficulty, mining_reward)


def create_transaction(inputs=None, outputs=None):
    """便捷函数：创建交易"""
    return Transaction(inputs, outputs)


# 网络相关便捷函数 (暂时注释掉，因为当前未使用)
# def create_network_node(node_id, difficulty=DEFAULT_DIFFICULTY,
#                         mining_reward=DEFAULT_MINING_REWARD):
#     """便捷函数：创建网络节点"""
#     return NetworkNode(node_id, difficulty, mining_reward)


# def create_distributed_network(difficulty=DEFAULT_DIFFICULTY, mining_reward=DEFAULT_MINING_REWARD):
#     """便捷函数：创建分布式网络"""
#     return DistributedNetwork(difficulty, mining_reward)


def create_difficulty_adjuster():
    """便捷函数：创建难度调整器"""
    return DifficultyAdjustment()


# 添加便捷函数到公开API
__all__.extend([
    'create_wallet',
    'create_blockchain',
    'create_transaction',
    # 'create_network_node',      # 暂时注释掉，因为当前未使用
    # 'create_distributed_network',  # 暂时注释掉，因为当前未使用
    'create_difficulty_adjuster'
])
