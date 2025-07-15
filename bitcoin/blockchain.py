#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⛓️ 区块链模块
包含区块和区块链核心管理功能
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple

from .config import (
    DEFAULT_DIFFICULTY, DEFAULT_MINING_REWARD, DEFAULT_TRANSACTION_FEE,
    HASH_DISPLAY_LENGTH
)
from .transaction import Transaction, UTXOSet
from .merkle_tree import MerkleTree, MerkleProof
from .utils import HashUtils


class Block:
    """区块类，表示区块链中的单个区块"""

    def __init__(self, index: int, transactions: List[Dict], previous_hash: str,
                 timestamp: Optional[str] = None, nonce: int = 0):
        """
        初始化区块
        Args:
            index: 区块索引
            transactions: 交易列表
            previous_hash: 前一个区块的哈希值
            timestamp: 时间戳
            nonce: 随机数，用于工作量证明
        """
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or str(int(time.time()))
        self.nonce = nonce

        # 构建Merkle树
        self.merkle_tree = None
        self.merkle_root = self._calculate_merkle_root()

        self.hash = self.calculate_hash()

    def _calculate_merkle_root(self) -> str:
        """计算Merkle根"""
        if not self.transactions:
            return "0" * 64  # 空区块的默认Merkle根

        # 使用Merkle树实现
        transaction_hashes = []
        for tx_data in self.transactions:
            if isinstance(tx_data, dict) and 'transaction_id' in tx_data:
                transaction_hashes.append(tx_data['transaction_id'])
            else:
                # 如果没有transaction_id，计算交易数据的哈希
                tx_str = json.dumps(tx_data, sort_keys=True)
                tx_hash = hashlib.sha256(tx_str.encode()).hexdigest()
                transaction_hashes.append(tx_hash)

        self.merkle_tree = MerkleTree(transaction_hashes)
        return self.merkle_tree.get_merkle_root() or "0" * 64

    def calculate_hash(self) -> str:
        """计算区块的哈希值"""
        return HashUtils.calculate_block_hash(
            self.index,
            self.merkle_root,
            self.previous_hash,
            self.timestamp,
            self.nonce
        )

    def mine_block(self, difficulty: int) -> None:
        """
        挖矿 - 工作量证明算法
        Args:
            difficulty: 挖矿难度（要求哈希值前缀有多少个0）
        """
        target = "0" * difficulty

        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

            # 每5000次尝试输出一次日志
            if self.nonce % 5000 == 0:
                print(f"⛏️  正在尝试 nonce: {self.nonce:,}, 当前哈希: {self.hash[:16]}...")

        print(f"🎯 挖矿成功! 最终 nonce: {self.nonce:,}, 区块哈希: {self.hash}")

    def get_merkle_proof(self, transaction_id: str) -> Optional[MerkleProof]:
        """
        获取指定交易的Merkle证明
        Args:
            transaction_id: 交易ID
        Returns:
            MerkleProof: Merkle证明，如果交易不存在则返回None
        """
        if not self.merkle_tree:
            return None

        return self.merkle_tree.get_merkle_proof(transaction_id)

    def verify_transaction_inclusion(self, transaction_id: str, merkle_proof: MerkleProof) -> bool:
        """
        验证交易是否包含在此区块中
        Args:
            transaction_id: 交易ID
            merkle_proof: Merkle证明
        Returns:
            bool: 是否包含该交易
        """
        # 使用Merkle证明验证
        if merkle_proof.merkle_root != self.merkle_root:
            return False

        # 验证证明中的目标哈希是否匹配
        if merkle_proof.target_hash != transaction_id:
            return False

        return MerkleTree.verify_merkle_proof(merkle_proof)

    def get_transaction_count(self) -> int:
        """获取区块中的交易数量"""
        return len(self.transactions)

    def get_block_size(self) -> int:
        """获取区块大小（字节）"""
        return len(json.dumps(self.to_dict()).encode())

    def to_dict(self) -> Dict[str, Any]:
        """将区块转换为字典格式"""
        result = {
            "index": self.index,
            "transactions": self.transactions,
            "merkle_root": self.merkle_root,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "hash": self.hash
        }

        # 包含Merkle树统计信息
        if self.merkle_tree:
            result["merkle_tree_stats"] = self.merkle_tree.get_statistics()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """从字典创建区块"""
        block = cls(
            index=data['index'],
            transactions=data['transactions'],
            previous_hash=data['previous_hash'],
            timestamp=data['timestamp'],
            nonce=data['nonce']
        )
        block.hash = data['hash']

        # 如果数据中包含merkle_root，使用它（用于兼容性）
        if 'merkle_root' in data:
            block.merkle_root = data['merkle_root']

        return block

    def __str__(self) -> str:
        """区块的字符串表示"""
        return f"区块 #{self.index} - 哈希: {self.hash[:HASH_DISPLAY_LENGTH]}..."


class UTXOFilter:
    """UTXO过滤工具类 - 提取重复的UTXO过滤逻辑"""

    @staticmethod
    def get_available_utxos(
            utxo_set,
            address: str,
            pending_transactions: List[Transaction]) -> List:
        """
        获取可用的UTXO（排除被待处理交易占用的）
        Args:
            utxo_set: UTXO集合
            address: 地址
            pending_transactions: 待处理交易列表
        Returns:
            List: 可用的UTXO列表
        """
        # 获取指定地址的所有UTXO
        available_utxos = utxo_set.get_utxos_by_address(address)

        # 收集被待处理交易占用的UTXO
        pending_used_utxos = set()
        for pending_tx in pending_transactions:
            for input_tx in pending_tx.inputs:
                pending_used_utxos.add(input_tx.get_utxo_id())

        # 过滤掉被占用的UTXO
        return [utxo for utxo in available_utxos
                if utxo.get_utxo_id() not in pending_used_utxos]

    @staticmethod
    def select_utxos_for_amount(utxos: List, amount: float, fee: float = 0) -> Tuple[List, float]:
        """
        为指定金额选择UTXO
        Args:
            utxos: 可用UTXO列表
            amount: 需要的金额
            fee: 手续费
        Returns:
            Tuple: (选中的UTXO列表, 总金额)
        """
        required_amount = amount + fee
        utxos.sort(key=lambda x: x.amount, reverse=True)  # 优先使用大额UTXO

        selected_utxos = []
        total_selected = 0.0

        for utxo in utxos:
            if total_selected >= required_amount:
                break
            selected_utxos.append(utxo)
            total_selected += utxo.amount

        return selected_utxos, total_selected


class TransactionHistoryCache:
    """交易历史缓存 - 优化性能"""

    def __init__(self):
        self.cache: Dict[str, List[Dict]] = {}  # address -> history
        self.last_block_index = -1

    def get_history(self, address: str, blockchain: 'Blockchain') -> List[Dict[str, Any]]:
        """
        获取交易历史（带缓存）
        Args:
            address: 地址
            blockchain: 区块链实例
        Returns:
            List: 交易历史
        """
        current_block_index = len(blockchain.chain) - 1

        # 如果缓存有效且没有新区块，直接返回缓存
        if (address in self.cache and
                self.last_block_index == current_block_index):
            return self.cache[address]

        # 重新计算历史记录
        history = self._calculate_history(address, blockchain)
        self.cache[address] = history
        self.last_block_index = current_block_index

        return history

    def _calculate_history(self, address: str, blockchain: 'Blockchain') -> List[Dict[str, Any]]:
        """计算交易历史"""
        history = []
        for block in blockchain.chain:
            for tx_data in block.transactions:
                try:
                    transaction = Transaction.from_dict(tx_data)
                    if self._is_address_involved(address, transaction, blockchain):
                        # 创建独立的发送和接收记录
                        entries = self._create_separate_history_entries(
                            address, transaction, block, blockchain.utxo_set, blockchain)
                        history.extend(entries)
                except Exception:
                    continue
        return history

    def _is_address_involved(
            self,
            address: str,
            transaction: Transaction,
            blockchain: 'Blockchain') -> bool:
        """检查地址是否参与交易"""
        # 检查输出地址
        if address in transaction.get_output_addresses():
            return True

        # 检查输入地址（使用历史查找方式）
        for input_tx in transaction.inputs:
            source_transaction = self._find_transaction_by_id(input_tx.transaction_id, blockchain)
            if source_transaction and input_tx.output_index < len(source_transaction.outputs):
                source_output = source_transaction.outputs[input_tx.output_index]
                if source_output.recipient_address == address:
                    return True

        return False

    def _create_history_entry(self, address: str, transaction: Transaction,
                              block, utxo_set, blockchain: 'Blockchain') -> Dict[str, Any]:
        """创建历史记录条目"""
        sent_amount = 0.0
        received_amount = 0.0

        # 计算发送和接收金额
        for output in transaction.outputs:
            if output.recipient_address == address:
                received_amount += output.amount

        # 修复：通过查找历史区块链中的交易来计算sent_amount
        for input_tx in transaction.inputs:
            if input_tx.transaction_id:  # 非coinbase交易
                # 查找输入交易引用的源交易
                source_transaction = self._find_transaction_by_id(
                    input_tx.transaction_id, blockchain)
                if source_transaction and input_tx.output_index < len(source_transaction.outputs):
                    source_output = source_transaction.outputs[input_tx.output_index]
                    if source_output.recipient_address == address:
                        sent_amount += source_output.amount

        # 确定交易类型
        # 修复：判断是否为真正的self交易（所有输入输出都是同一个地址）
        is_self_transaction = (
            sent_amount > 0 and received_amount > 0 and
            all(output.recipient_address == address for output in transaction.outputs)
        )

        if is_self_transaction:
            tx_type = "self"
        elif sent_amount > 0:
            tx_type = "sent"
        else:
            tx_type = "received"

        # 确定对方地址
        from_address = None
        to_address = None

        if transaction.is_coinbase():
            # 挖矿奖励交易
            from_address = 'Genesis'
            to_address = address
        else:
            # 普通交易
            if tx_type == 'received':
                # 接收交易：查找发送方地址
                from_address = self._find_sender_address(transaction, address, blockchain)
                to_address = address
            else:
                # 发送交易：查找接收方地址
                from_address = address
                for output in transaction.outputs:
                    if output.recipient_address != address:
                        to_address = output.recipient_address
                        break

        return {
            'block_index': block.index,
            'transaction_id': transaction.transaction_id,
            'inputs': len(transaction.inputs),
            'outputs': len(transaction.outputs),
            'sent_amount': sent_amount,
            'received_amount': received_amount,
            'net_amount': received_amount - sent_amount,
            'fee': transaction.calculate_fee(utxo_set),
            'timestamp': transaction.timestamp,
            'type': tx_type,
            'is_coinbase': transaction.is_coinbase(),
            'from_address': from_address,
            'to_address': to_address
        }

    def _find_sender_address(
            self,
            transaction: Transaction,
            receiver_address: str,
            blockchain: 'Blockchain') -> Optional[str]:
        """
        查找交易的发送方地址
        通过遍历区块链历史来找到输入交易的来源地址
        """
        for input_tx in transaction.inputs:
            # 查找输入交易引用的源交易
            source_transaction = self._find_transaction_by_id(input_tx.transaction_id, blockchain)
            if source_transaction:
                # 找到源交易的对应输出
                if input_tx.output_index < len(source_transaction.outputs):
                    source_output = source_transaction.outputs[input_tx.output_index]
                    # 如果这个输出不是发给接收方的，那么就是发送方地址
                    if source_output.recipient_address != receiver_address:
                        return source_output.recipient_address

        return None

    def _find_transaction_by_id(
            self,
            transaction_id: str,
            blockchain: 'Blockchain') -> Optional[Transaction]:
        """
        根据交易ID在区块链中查找交易（使用索引优化）
        """
        # 首先尝试使用索引快速查找
        if transaction_id in blockchain.transaction_index:
            block_index, tx_index = blockchain.transaction_index[transaction_id]
            try:
                if block_index < len(blockchain.chain):
                    block = blockchain.chain[block_index]
                    if tx_index < len(block.transactions):
                        tx_data = block.transactions[tx_index]
                        return Transaction.from_dict(tx_data)
            except Exception:
                pass

        # 如果索引查找失败，回退到遍历查找（兼容性）
        for block in blockchain.chain:
            for tx_data in block.transactions:
                try:
                    transaction = Transaction.from_dict(tx_data)
                    if transaction.transaction_id == transaction_id:
                        return transaction
                except Exception:
                    continue
        return None

    def _is_change_transaction(
            self,
            transaction: Transaction,
            address: str,
            blockchain: 'Blockchain') -> bool:
        """
        判断是否为找零交易
        找零交易的特点：用户既是输入的所有者，也是输出的接收者
        """
        # 检查交易输入是否包含用户的UTXO
        user_has_input = False
        for input_tx in transaction.inputs:
            source_transaction = self._find_transaction_by_id(input_tx.transaction_id, blockchain)
            if source_transaction and input_tx.output_index < len(source_transaction.outputs):
                source_output = source_transaction.outputs[input_tx.output_index]
                if source_output.recipient_address == address:
                    user_has_input = True
                    break

        # 检查交易输出是否包含给其他人的转账
        has_external_output = False
        for output in transaction.outputs:
            if output.recipient_address != address:
                has_external_output = True
                break

        # 如果用户有输入且存在外部输出，则当前的接收是找零
        return user_has_input and has_external_output

    def _create_separate_history_entries(self,
                                         address: str,
                                         transaction: Transaction,
                                         block,
                                         utxo_set,
                                         blockchain: 'Blockchain') -> List[Dict[str,
                                                                                Any]]:
        """创建独立的发送和接收历史记录"""
        entries = []

        # 计算发送和接收金额
        sent_amount = 0.0
        received_amount = 0.0

        # 计算接收金额
        for output in transaction.outputs:
            if output.recipient_address == address:
                received_amount += output.amount

        # 计算发送金额（通过查找历史区块链中的交易）
        for input_tx in transaction.inputs:
            if input_tx.transaction_id:  # 非coinbase交易
                source_transaction = self._find_transaction_by_id(
                    input_tx.transaction_id, blockchain)
                if source_transaction and input_tx.output_index < len(source_transaction.outputs):
                    source_output = source_transaction.outputs[input_tx.output_index]
                    if source_output.recipient_address == address:
                        sent_amount += source_output.amount

        # 判断是否为纯粹的self交易（所有输入输出都是同一个地址）
        is_pure_self_transaction = (
            sent_amount > 0 and received_amount > 0 and
            all(output.recipient_address == address for output in transaction.outputs) and
            not transaction.is_coinbase()
        )

        # 如果是纯粹的self交易，创建一条记录
        if is_pure_self_transaction:
            entries.append(self._create_single_history_entry(
                address, transaction, block, utxo_set, blockchain,
                sent_amount, received_amount, "self"))
        else:
            # 创建独立的发送和接收记录
            if sent_amount > 0:
                # 创建发送记录
                entries.append(self._create_single_history_entry(
                    address, transaction, block, utxo_set, blockchain,
                    sent_amount, 0.0, "sent"))

            if received_amount > 0:
                # 创建接收记录
                entries.append(self._create_single_history_entry(
                    address, transaction, block, utxo_set, blockchain,
                    0.0, received_amount, "received"))

        return entries

    def _create_single_history_entry(self, address: str, transaction: Transaction,
                                     block, utxo_set, blockchain: 'Blockchain',
                                     sent_amount: float, received_amount: float,
                                     tx_type: str) -> Dict[str, Any]:
        """创建单个历史记录条目"""
        # 确定对方地址
        from_address = None
        to_address = None

        if transaction.is_coinbase():
            # 挖矿奖励交易
            from_address = 'Genesis'
            to_address = address
        else:
            # 普通交易
            if tx_type == 'sent':
                # 发送交易：查找接收方地址
                from_address = address
                for output in transaction.outputs:
                    if output.recipient_address != address:
                        to_address = output.recipient_address
                        break
            elif tx_type == 'received':
                # 接收交易：需要判断是否为找零交易
                sender_address = self._find_sender_address(transaction, address, blockchain)

                # 如果找不到发送方地址，可能是找零交易
                if sender_address is None:
                    # 检查是否为找零交易（用户自己给自己的转账）
                    if self._is_change_transaction(transaction, address, blockchain):
                        from_address = address  # 找零交易，发送方是自己
                    else:
                        from_address = None  # 真的找不到发送方
                else:
                    from_address = sender_address

                to_address = address
            else:  # self交易
                from_address = address
                to_address = address

        return {
            'block_index': block.index,
            'transaction_id': transaction.transaction_id,
            'inputs': len(transaction.inputs),
            'outputs': len(transaction.outputs),
            'sent_amount': sent_amount,
            'received_amount': received_amount,
            'net_amount': received_amount - sent_amount,
            'fee': transaction.calculate_fee(utxo_set),
            'timestamp': transaction.timestamp,
            'type': tx_type,
            'is_coinbase': transaction.is_coinbase(),
            'from_address': from_address,
            'to_address': to_address
        }

    def invalidate_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.last_block_index = -1


class Blockchain:
    """区块链类，管理整个区块链系统 - 支持UTXO模型"""

    def __init__(self, difficulty: int = DEFAULT_DIFFICULTY,
                 mining_reward: float = DEFAULT_MINING_REWARD):
        """
        初始化区块链
        Args:
            difficulty: 挖矿难度
            mining_reward: 挖矿奖励
        """
        self.difficulty = difficulty
        self.pending_transactions = []
        self.mining_reward = mining_reward
        self.utxo_set = UTXOSet()  # UTXO集合
        self.history_cache = TransactionHistoryCache()  # 交易历史缓存
        self.transaction_index = {}  # 交易ID索引：{transaction_id: (block_index, tx_index)}
        # 创建创世区块（必须在其他属性初始化后）
        self.chain = [self.create_genesis_block()]
        # 重建完整的交易索引
        self._rebuild_transaction_index()

    def create_genesis_block(self) -> Block:
        """创建创世区块"""
        # 创建创世交易
        genesis_transaction = Transaction.create_coinbase_transaction("genesis", 0)
        genesis_block = Block(
            index=0,
            transactions=[genesis_transaction.to_dict()],
            previous_hash="0"
        )
        # 直接设置创世区块的哈希，不需要挖矿
        genesis_block.hash = genesis_block.calculate_hash()
        # 初始化UTXO集合
        self._update_utxo_set([genesis_transaction])
        # 更新交易索引
        self._update_transaction_index(genesis_block)
        return genesis_block

    def get_latest_block(self) -> Block:
        """获取最新的区块"""
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> bool:
        """
        添加交易到待处理交易池
        Args:
            transaction: 要添加的交易
        Returns:
            bool: 是否成功添加
        """
        if not transaction.is_valid(self.utxo_set):
            return False

        # 检查UTXO有效性（跳过挖矿奖励交易）
        if transaction.inputs:  # 非coinbase交易
            if not self._validate_transaction_utxos(transaction):
                return False

        self.pending_transactions.append(transaction)
        # 交易池变化时清空历史缓存
        self.history_cache.invalidate_cache()
        return True

    def _validate_transaction_utxos(self, transaction: Transaction) -> bool:
        """验证交易的UTXO有效性"""
        total_input = 0

        # 收集被待处理交易占用的UTXO
        pending_used_utxos = set()
        for pending_tx in self.pending_transactions:
            for input_tx in pending_tx.inputs:
                pending_used_utxos.add(input_tx.get_utxo_id())

        for input_tx in transaction.inputs:
            utxo_id = input_tx.get_utxo_id()

            # 检查UTXO是否存在于UTXO集合中
            if utxo_id not in self.utxo_set:
                return False

            # 检查UTXO是否已被待处理交易占用（防止双花）
            if utxo_id in pending_used_utxos:
                return False

            utxo = self.utxo_set[utxo_id]

            # 检查UTXO是否已被花费
            if utxo.is_spent:
                return False

            total_input += utxo.amount

        total_output = sum(output.amount for output in transaction.outputs)
        return total_input >= total_output

    def mine_pending_transactions(self, mining_reward_address: str) -> Optional[Block]:
        """
        挖矿处理待处理的交易
        Args:
            mining_reward_address: 接收挖矿奖励的地址
        Returns:
            Block: 新挖出的区块
        """

        # 计算总手续费
        total_fees = sum(tx.calculate_fee(self.utxo_set) for tx in self.pending_transactions)

        # 创建挖矿奖励交易（包含手续费和区块高度信息）
        reward_transaction = Transaction.create_coinbase_transaction(
            mining_reward_address,
            self.mining_reward + total_fees,
            block_height=len(self.chain)  # 直接在创建时传入区块高度
        )

        # 准备交易数据
        transactions_data = [tx.to_dict() for tx in self.pending_transactions]
        transactions_data.append(reward_transaction.to_dict())

        # 创建新区块
        block = Block(
            index=len(self.chain),
            transactions=transactions_data,
            previous_hash=self.get_latest_block().hash
        )

        # 挖矿
        block.mine_block(self.difficulty)

        # 将区块添加到链中
        self.chain.append(block)

        # 更新UTXO集合
        self._update_utxo_set(self.pending_transactions + [reward_transaction])

        # 更新交易索引
        self._update_transaction_index(block)

        # 清空待处理交易
        self.pending_transactions = []

        # 清空历史缓存
        self.history_cache.invalidate_cache()

        return block

    def _update_utxo_set(self, transactions: List[Transaction]) -> None:
        """
        更新UTXO集合
        Args:
            transactions: 交易列表
        """
        for transaction in transactions:
            self.utxo_set.update_from_transaction(transaction)

    def _update_transaction_index(self, block: Block) -> None:
        """
        更新交易索引
        Args:
            block: 要索引的区块
        """
        block_index = block.index
        for tx_index, tx_data in enumerate(block.transactions):
            if isinstance(tx_data, dict):
                transaction_id = tx_data.get('transaction_id')
            else:
                transaction_id = tx_data.transaction_id

            if transaction_id:
                self.transaction_index[transaction_id] = (block_index, tx_index)

    def _rebuild_transaction_index(self) -> None:
        """
        重建完整的交易索引
        用于系统启动或索引损坏时重建索引
        """
        self.transaction_index.clear()
        for block in self.chain:
            self._update_transaction_index(block)

    def get_balance(self, address: str) -> float:
        """
        获取指定地址的余额
        Args:
            address: 要查询的地址
        Returns:
            float: 账户余额
        """
        # 优先使用UTXO计算余额
        return self.utxo_set.get_balance(address)

    def create_utxo_transaction(
            self,
            from_address: str,
            to_address: str,
            amount: float,
            fee: float = DEFAULT_TRANSACTION_FEE,
            wallet=None) -> Optional[Transaction]:
        """
        创建UTXO交易（简化版本）
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 交易金额
            fee: 手续费
            wallet: 钱包对象（用于签名）
        Returns:
            Transaction: 创建的交易，如果余额不足则返回None
        """
        # 获取可用UTXO
        available_utxos = UTXOFilter.get_available_utxos(
            self.utxo_set, from_address, self.pending_transactions)

        # 选择足够的UTXO
        selected_utxos, total_selected = UTXOFilter.select_utxos_for_amount(
            available_utxos, amount, fee)

        # 检查余额是否足够
        if total_selected < amount + fee:
            return None

        # 创建交易
        transaction = self._build_transaction(
            selected_utxos, to_address, from_address, amount, fee, total_selected)

        # 签名交易
        if wallet:
            transaction.sign_transaction(wallet, self.utxo_set)

        return transaction

    def _build_transaction(self, selected_utxos: List, to_address: str,
                           from_address: str, amount: float, fee: float,
                           total_input: float) -> Transaction:
        """构建交易对象"""
        from .transaction import TransactionInput, TransactionOutput

        # 创建输入
        inputs = [TransactionInput(utxo.transaction_id, utxo.output_index)
                  for utxo in selected_utxos]

        # 创建输出
        outputs = [TransactionOutput(amount, to_address)]

        # 如果有找零，创建找零输出
        change = total_input - amount - fee
        if change > 0:
            outputs.append(TransactionOutput(change, from_address))

        return Transaction(inputs=inputs, outputs=outputs)

    def get_utxos_by_address(self, address: str) -> List:
        """
        获取指定地址的所有可用UTXO
        Args:
            address: 地址
        Returns:
            List[UTXO]: UTXO列表
        """
        return self.utxo_set.get_utxos_by_address(address)

    def get_transaction_history(self, address: str) -> List[Dict[str, Any]]:
        """
        获取指定地址的交易历史（优化版本）
        Args:
            address: 要查询的地址
        Returns:
            List[Dict]: 交易历史列表
        """
        return self.history_cache.get_history(address, self)

    def is_chain_valid(self) -> bool:
        """
        验证整个区块链是否有效
        Returns:
            bool: 区块链是否有效
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # 验证当前区块的哈希值
            if current_block.hash != current_block.calculate_hash():
                return False

            # 验证前一个区块的哈希值
            if current_block.previous_hash != previous_block.hash:
                return False

            # 验证挖矿难度
            if current_block.hash[:self.difficulty] != "0" * self.difficulty:
                return False

            # 验证区块中的交易（仅基本格式验证，不验证UTXO状态）
            for tx_data in current_block.transactions:
                try:
                    transaction = Transaction.from_dict(tx_data)

                    # 仅进行基本验证，不检查UTXO状态
                    # 因为历史交易的UTXO已经被消费，无法在当前UTXO集合中找到

                    # 检查交易格式
                    if not transaction.inputs and not transaction.is_coinbase():
                        return False  # 非coinbase交易必须有输入

                    # 检查输出金额为正数
                    for output in transaction.outputs:
                        if output.amount <= 0:
                            return False

                    # Coinbase交易必须有输出
                    if transaction.is_coinbase() and len(transaction.outputs) == 0:
                        return False

                except Exception as e:
                    return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """将区块链转换为字典格式"""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "difficulty": self.difficulty,
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
            "mining_reward": self.mining_reward,
            "utxo_set": {utxo_id: utxo.to_dict() for utxo_id, utxo in self.utxo_set.utxos.items()}
        }

    def save_to_file(self, filename: str) -> None:
        """将区块链保存到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filename: str) -> 'Blockchain':
        """从文件加载区块链"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 创建区块链实例
            blockchain = cls(data['difficulty'], data['mining_reward'])

            # 重建区块链
            blockchain.chain = []
            for block_data in data['chain']:
                block = Block.from_dict(block_data)
                blockchain.chain.append(block)

            # 重建待处理交易
            blockchain.pending_transactions = []
            for tx_data in data['pending_transactions']:
                tx = Transaction.from_dict(tx_data)
                blockchain.pending_transactions.append(tx)

            # 恢复UTXO集合
            if 'utxo_set' in data:
                blockchain.utxo_set = UTXOSet()
                for utxo_id, utxo_data in data['utxo_set'].items():
                    from .transaction import UTXO
                    utxo = UTXO.from_dict(utxo_data)
                    blockchain.utxo_set.utxos[utxo_id] = utxo

            return blockchain
        except Exception as e:
            raise

    def get_merkle_proof_for_transaction(
            self, transaction_id: str) -> Optional[Tuple[int, MerkleProof]]:
        """
        获取指定交易的Merkle证明
        Args:
            transaction_id: 交易ID
        Returns:
            Tuple[int, MerkleProof]: (区块索引, Merkle证明)，如果交易不存在则返回None
        """
        for block_index, block in enumerate(self.chain):
            for tx_data in block.transactions:
                if isinstance(tx_data, dict) and tx_data.get('transaction_id') == transaction_id:
                    proof = block.get_merkle_proof(transaction_id)
                    if proof:
                        return (block_index, proof)
        return None

    def verify_transaction_with_merkle_proof(self, transaction_id: str, block_index: int,
                                             merkle_proof: MerkleProof) -> bool:
        """
        使用Merkle证明验证交易
        Args:
            transaction_id: 交易ID
            block_index: 区块索引
            merkle_proof: Merkle证明
        Returns:
            bool: 验证是否成功
        """
        if block_index < 0 or block_index >= len(self.chain):
            return False

        block = self.chain[block_index]
        return block.verify_transaction_inclusion(transaction_id, merkle_proof)

    def get_block_merkle_stats(self, block_index: int) -> Optional[Dict[str, Any]]:
        """
        获取指定区块的Merkle树统计信息
        Args:
            block_index: 区块索引
        Returns:
            Dict: Merkle树统计信息，如果区块不存在则返回None
        """
        if block_index < 0 or block_index >= len(self.chain):
            return None

        block = self.chain[block_index]
        if not hasattr(block, 'merkle_tree') or not block.merkle_tree:
            return None

        return block.merkle_tree.get_statistics()

    def export_merkle_proofs(self, filename: str) -> bool:
        """
        导出所有交易的Merkle证明
        Args:
            filename: 导出文件名
        Returns:
            bool: 是否成功导出
        """
        try:
            proofs_data = {
                'blockchain_info': BlockchainDisplay.get_chain_info(self),
                'merkle_proofs': []
            }

            for block_index, block in enumerate(self.chain):
                if hasattr(block, 'merkle_tree') and block.merkle_tree:
                    for tx_data in block.transactions:
                        if isinstance(tx_data, dict) and 'transaction_id' in tx_data:
                            tx_id = tx_data['transaction_id']
                            proof = block.get_merkle_proof(tx_id)
                            if proof:
                                proofs_data['merkle_proofs'].append({
                                    'block_index': block_index,
                                    'transaction_id': tx_id,
                                    'merkle_proof': proof.to_dict()
                                })

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(proofs_data, f, indent=2, ensure_ascii=False)
            return True

        except Exception as e:
            return False

    def __str__(self) -> str:
        """区块链的字符串表示"""
        return f"区块链 - {len(self.chain)} 个区块, {len(self.utxo_set.utxos)} 个UTXO, Merkle树: 启用"


class BlockchainDisplay:
    """区块链显示工具类 - 分离UI逻辑"""

    @staticmethod
    def get_chain_info(blockchain: Blockchain) -> Dict[str, Any]:
        """获取区块链信息"""
        total_transactions = sum(len(block.transactions) for block in blockchain.chain)

        # 计算Merkle树统计
        total_merkle_proofs = 0
        for block in blockchain.chain:
            if hasattr(block, 'merkle_tree') and block.merkle_tree:
                total_merkle_proofs += len(block.transactions)

        return {
            "区块高度": blockchain.get_latest_block().index,
            "交易总数": total_transactions,
            "当前难度": blockchain.difficulty,
            "挖矿奖励": blockchain.mining_reward,
            "待处理交易": len(blockchain.pending_transactions),
            "UTXO总数": len(blockchain.utxo_set.utxos),
            "最新区块哈希": blockchain.get_latest_block().hash[:HASH_DISPLAY_LENGTH] + "...",
            "Merkle树支持": "启用",
            "可验证交易数": total_merkle_proofs,
            "链是否有效": blockchain.is_chain_valid()
        }

    @staticmethod
    def print_chain_status(blockchain: Blockchain) -> None:
        """打印区块链状态"""
        print("\n=== 📊 区块链状态 ===")
        info = BlockchainDisplay.get_chain_info(blockchain)
        for key, value in info.items():
            print(f"{key}: {value}")

        print("\n=== 💰 地址余额 ===")
        utxo_by_address = {}
        for utxo in blockchain.utxo_set.utxos.values():
            if not utxo.is_spent:
                if utxo.recipient_address not in utxo_by_address:
                    utxo_by_address[utxo.recipient_address] = 0
                utxo_by_address[utxo.recipient_address] += utxo.amount

        if utxo_by_address:
            for address, balance in utxo_by_address.items():
                print(f"地址 {address[:16]}...: {balance} BTC")
        else:
            print("暂无账户余额")

        print(f"\n=== 📋 待处理交易 ({len(blockchain.pending_transactions)}) ===")
        if blockchain.pending_transactions:
            for i, tx in enumerate(blockchain.pending_transactions, 1):
                print(f"{i}. {tx}")
        else:
            print("无待处理交易")
