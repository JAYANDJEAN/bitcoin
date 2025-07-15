#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⛓️ 以太坊区块链

实现以太坊区块链结构：
- 区块结构
- 交易结构
- 区块链管理
- 状态管理
"""

import hashlib
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class EthereumTransaction:
    """以太坊交易"""
    from_address: str
    to_address: str
    value: int  # wei
    gas_limit: int
    gas_price: int
    data: str = ""
    nonce: int = 0
    signature: str = ""
    transaction_hash: str = field(default="", init=False)
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def __post_init__(self):
        """计算交易哈希"""
        if not self.transaction_hash:
            self.transaction_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """计算交易哈希"""
        transaction_data = {
            "from": self.from_address,
            "to": self.to_address,
            "value": self.value,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "data": self.data,
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }

        transaction_str = json.dumps(transaction_data, sort_keys=True)
        return hashlib.sha256(transaction_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hash": self.transaction_hash,
            "from": self.from_address,
            "to": self.to_address,
            "value": self.value,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "data": self.data,
            "nonce": self.nonce,
            "signature": self.signature,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EthereumTransaction':
        """从字典创建交易"""
        return cls(
            from_address=data["from"],
            to_address=data["to"],
            value=data["value"],
            gas_limit=data["gas_limit"],
            gas_price=data["gas_price"],
            data=data.get("data", ""),
            nonce=data.get("nonce", 0),
            signature=data.get("signature", ""),
            timestamp=data.get("timestamp", int(time.time()))
        )

    def __str__(self) -> str:
        return f"Transaction({self.transaction_hash[:10]}...)"


@dataclass
class EthereumBlock:
    """以太坊区块"""
    block_number: int
    parent_hash: str
    transactions: List[EthereumTransaction]
    state_root: str = ""
    transactions_root: str = ""
    receipts_root: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))
    gas_limit: int = 8000000
    gas_used: int = 0
    miner: str = ""
    difficulty: int = 1000000
    nonce: int = 0
    block_hash: str = field(default="", init=False)

    def __post_init__(self):
        """计算区块哈希"""
        if not self.block_hash:
            self.block_hash = self.calculate_hash()

        if not self.transactions_root:
            self.transactions_root = self.calculate_transactions_root()

    def calculate_hash(self) -> str:
        """计算区块哈希"""
        block_data = {
            "number": self.block_number,
            "parent_hash": self.parent_hash,
            "transactions_root": self.transactions_root,
            "state_root": self.state_root,
            "timestamp": self.timestamp,
            "gas_limit": self.gas_limit,
            "gas_used": self.gas_used,
            "miner": self.miner,
            "difficulty": self.difficulty,
            "nonce": self.nonce
        }

        block_str = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_str.encode()).hexdigest()

    def calculate_transactions_root(self) -> str:
        """计算交易根哈希"""
        if not self.transactions:
            return "0" * 64

        transaction_hashes = [tx.transaction_hash for tx in self.transactions]
        combined = "".join(transaction_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()

    def add_transaction(self, transaction: EthereumTransaction):
        """添加交易"""
        self.transactions.append(transaction)
        self.gas_used += transaction.gas_limit

        # 重新计算根哈希
        self.transactions_root = self.calculate_transactions_root()
        self.block_hash = self.calculate_hash()

    def get_transaction_count(self) -> int:
        """获取交易数量"""
        return len(self.transactions)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hash": self.block_hash,
            "number": self.block_number,
            "parent_hash": self.parent_hash,
            "transactions_root": self.transactions_root,
            "state_root": self.state_root,
            "receipts_root": self.receipts_root,
            "timestamp": self.timestamp,
            "gas_limit": self.gas_limit,
            "gas_used": self.gas_used,
            "miner": self.miner,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "transactions": [tx.to_dict() for tx in self.transactions]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EthereumBlock':
        """从字典创建区块"""
        transactions = [
            EthereumTransaction.from_dict(tx_data)
            for tx_data in data.get("transactions", [])
        ]

        return cls(
            block_number=data["number"],
            parent_hash=data["parent_hash"],
            transactions=transactions,
            state_root=data.get("state_root", ""),
            transactions_root=data.get("transactions_root", ""),
            receipts_root=data.get("receipts_root", ""),
            timestamp=data.get("timestamp", int(time.time())),
            gas_limit=data.get("gas_limit", 8000000),
            gas_used=data.get("gas_used", 0),
            miner=data.get("miner", ""),
            difficulty=data.get("difficulty", 1000000),
            nonce=data.get("nonce", 0)
        )

    def __str__(self) -> str:
        return f"Block(#{self.block_number}, {len(self.transactions)} txs)"


class EthereumBlockchain:
    """以太坊区块链"""

    def __init__(self):
        self.blocks: List[EthereumBlock] = []
        self.pending_transactions: List[EthereumTransaction] = []
        self.transaction_pool: Dict[str, EthereumTransaction] = {}
        self.state: Dict[str, Any] = {}  # 世界状态
        self.chain_id = 1

        # 创建创世区块
        self._create_genesis_block()

    def _create_genesis_block(self):
        """创建创世区块"""
        genesis_block = EthereumBlock(
            block_number=0,
            parent_hash="0" * 64,
            transactions=[],
            miner="0x0000000000000000000000000000000000000000",
            timestamp=int(time.time())
        )

        self.blocks.append(genesis_block)

    def get_latest_block(self) -> EthereumBlock:
        """获取最新区块"""
        return self.blocks[-1] if self.blocks else None

    def get_block_by_number(self, block_number: int) -> Optional[EthereumBlock]:
        """根据区块号获取区块"""
        if 0 <= block_number < len(self.blocks):
            return self.blocks[block_number]
        return None

    def get_block_by_hash(self, block_hash: str) -> Optional[EthereumBlock]:
        """根据区块哈希获取区块"""
        for block in self.blocks:
            if block.block_hash == block_hash:
                return block
        return None

    def add_transaction(self, transaction: EthereumTransaction):
        """添加交易到交易池"""
        self.pending_transactions.append(transaction)
        self.transaction_pool[transaction.transaction_hash] = transaction

    def get_transaction(self, tx_hash: str) -> Optional[EthereumTransaction]:
        """获取交易"""
        # 先在交易池中查找
        if tx_hash in self.transaction_pool:
            return self.transaction_pool[tx_hash]

        # 在区块中查找
        for block in self.blocks:
            for tx in block.transactions:
                if tx.transaction_hash == tx_hash:
                    return tx

        return None

    def mine_block(self, miner_address: str, max_transactions: int = 100) -> EthereumBlock:
        """挖矿创建新区块"""
        latest_block = self.get_latest_block()

        # 选择待处理的交易
        selected_transactions = self.pending_transactions[:max_transactions]

        # 创建新区块
        new_block = EthereumBlock(
            block_number=latest_block.block_number + 1,
            parent_hash=latest_block.block_hash,
            transactions=selected_transactions.copy(),
            miner=miner_address
        )

        # 计算Gas使用量
        total_gas_used = sum(tx.gas_limit for tx in selected_transactions)
        new_block.gas_used = total_gas_used

        # 添加区块到链中
        self.blocks.append(new_block)

        # 从待处理交易中移除已打包的交易
        for tx in selected_transactions:
            if tx in self.pending_transactions:
                self.pending_transactions.remove(tx)
            # 保留在交易池中以便查询

        return new_block

    def get_balance(self, address: str) -> int:
        """获取地址余额"""
        return self.state.get(f"balance_{address}", 0)

    def set_balance(self, address: str, balance: int):
        """设置地址余额"""
        self.state[f"balance_{address}"] = balance

    def transfer_balance(self, from_address: str, to_address: str, amount: int) -> bool:
        """转移余额"""
        from_balance = self.get_balance(from_address)
        if from_balance < amount:
            return False

        self.set_balance(from_address, from_balance - amount)
        to_balance = self.get_balance(to_address)
        self.set_balance(to_address, to_balance + amount)

        return True

    def get_chain_length(self) -> int:
        """获取区块链长度"""
        return len(self.blocks)

    def get_total_difficulty(self) -> int:
        """获取总难度"""
        return sum(block.difficulty for block in self.blocks)

    def validate_block(self, block: EthereumBlock) -> bool:
        """验证区块"""
        # 检查区块号
        latest_block = self.get_latest_block()
        if block.block_number != latest_block.block_number + 1:
            return False

        # 检查父哈希
        if block.parent_hash != latest_block.block_hash:
            return False

        # 检查交易根哈希
        expected_tx_root = block.calculate_transactions_root()
        if block.transactions_root != expected_tx_root:
            return False

        # 检查区块哈希
        expected_hash = block.calculate_hash()
        if block.block_hash != expected_hash:
            return False

        return True

    def validate_transaction(self, transaction: EthereumTransaction) -> bool:
        """验证交易"""
        # 检查交易哈希
        expected_hash = transaction.calculate_hash()
        if transaction.transaction_hash != expected_hash:
            return False

        # 检查余额（简化验证）
        sender_balance = self.get_balance(transaction.from_address)
        total_cost = transaction.value + (transaction.gas_limit * transaction.gas_price)
        if sender_balance < total_cost:
            return False

        return True

    def get_pending_transactions_count(self) -> int:
        """获取待处理交易数量"""
        return len(self.pending_transactions)

    def get_blockchain_info(self) -> Dict[str, Any]:
        """获取区块链信息"""
        latest_block = self.get_latest_block()

        return {
            "chain_id": self.chain_id,
            "latest_block_number": latest_block.block_number if latest_block else 0,
            "latest_block_hash": latest_block.block_hash if latest_block else "",
            "total_blocks": len(self.blocks),
            "pending_transactions": len(self.pending_transactions),
            "total_difficulty": self.get_total_difficulty(),
            "average_block_time": self._calculate_average_block_time()
        }

    def _calculate_average_block_time(self) -> float:
        """计算平均出块时间"""
        if len(self.blocks) < 2:
            return 0.0

        total_time = 0
        for i in range(1, len(self.blocks)):
            time_diff = self.blocks[i].timestamp - self.blocks[i - 1].timestamp
            total_time += time_diff

        return total_time / (len(self.blocks) - 1)

    def export_blockchain(self) -> Dict[str, Any]:
        """导出区块链数据"""
        return {
            "chain_id": self.chain_id,
            "blocks": [block.to_dict() for block in self.blocks],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
            "state": self.state.copy(),
            "export_timestamp": int(time.time())
        }

    def import_blockchain(self, blockchain_data: Dict[str, Any]):
        """导入区块链数据"""
        self.chain_id = blockchain_data.get("chain_id", 1)
        self.state = blockchain_data.get("state", {})

        # 导入区块
        self.blocks = []
        for block_data in blockchain_data.get("blocks", []):
            block = EthereumBlock.from_dict(block_data)
            self.blocks.append(block)

        # 导入待处理交易
        self.pending_transactions = []
        self.transaction_pool = {}
        for tx_data in blockchain_data.get("pending_transactions", []):
            tx = EthereumTransaction.from_dict(tx_data)
            self.pending_transactions.append(tx)
            self.transaction_pool[tx.transaction_hash] = tx

    def get_transaction_history(self, address: str) -> List[EthereumTransaction]:
        """获取地址的交易历史"""
        transactions = []

        for block in self.blocks:
            for tx in block.transactions:
                if tx.from_address == address or tx.to_address == address:
                    transactions.append(tx)

        return transactions

    def __str__(self) -> str:
        return f"EthereumBlockchain(blocks={len(self.blocks)}, pending_txs={len(self.pending_transactions)})"
