#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌳 Merkle树实现

Merkle树是比特币的核心数据结构：
- 每个叶子节点是一个交易的哈希
- 每个内部节点是其子节点哈希的哈希
- 根节点包含所有交易的"指纹"
- 支持高效的交易存在性证明(SPV)
"""

import hashlib
import json
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import time as time_module


@dataclass
class MerkleNode:
    """Merkle树节点"""
    hash_value: str              # 节点哈希值
    left: Optional['MerkleNode'] = None   # 左子节点
    right: Optional['MerkleNode'] = None  # 右子节点
    data: Optional[str] = None   # 叶子节点数据

    def is_leaf(self) -> bool:
        """判断是否为叶子节点"""
        return self.left is None and self.right is None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'hash': self.hash_value,
            'is_leaf': self.is_leaf()
        }
        if self.data:
            result['data'] = self.data
        if self.left:
            result['left'] = self.left.to_dict()
        if self.right:
            result['right'] = self.right.to_dict()
        return result


@dataclass
class MerkleProof:
    """Merkle证明"""
    target_hash: str             # 目标交易哈希
    merkle_root: str            # Merkle根
    proof_hashes: List[str]     # 证明路径上的哈希
    proof_directions: List[bool]  # 证明路径方向 (True=右, False=左)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'target_hash': self.target_hash,
            'merkle_root': self.merkle_root,
            'proof_hashes': self.proof_hashes,
            'proof_directions': self.proof_directions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MerkleProof':
        """从字典创建"""
        return cls(
            target_hash=data['target_hash'],
            merkle_root=data['merkle_root'],
            proof_hashes=data['proof_hashes'],
            proof_directions=data['proof_directions']
        )


class MerkleTree:
    """Merkle树"""

    def __init__(self, transactions: List[str] = None):
        """
        初始化Merkle树

        Args:
            transactions: 交易哈希列表
        """
        self.transactions = transactions or []
        self.root: Optional[MerkleNode] = None
        self.leaves: List[MerkleNode] = []

        if self.transactions:
            self.build_tree()

    def add_transaction(self, tx_hash: str):
        """添加交易"""
        self.transactions.append(tx_hash)
        self.build_tree()

    def build_tree(self):
        """构建Merkle树"""
        if not self.transactions:
            self.root = None
            self.leaves = []
            return

        # 1. 创建叶子节点
        self.leaves = []
        for tx_hash in self.transactions:
            # 对交易哈希再次哈希（比特币的做法）
            leaf_hash = self._double_sha256(tx_hash)
            leaf_node = MerkleNode(hash_value=leaf_hash, data=tx_hash)
            self.leaves.append(leaf_node)

        # 2. 如果交易数量为奇数，复制最后一个交易（比特币的做法）
        current_level = self.leaves.copy()

        # 3. 逐层构建树
        while len(current_level) > 1:
            next_level = []

            # 处理每一对节点
            for i in range(0, len(current_level), 2):
                left_node = current_level[i]

                # 如果是奇数个节点，复制最后一个
                if i + 1 < len(current_level):
                    right_node = current_level[i + 1]
                else:
                    right_node = current_level[i]  # 复制左节点

                # 创建父节点
                parent_hash = self._double_sha256(left_node.hash_value + right_node.hash_value)
                parent_node = MerkleNode(
                    hash_value=parent_hash,
                    left=left_node,
                    right=right_node
                )
                next_level.append(parent_node)

            current_level = next_level

        # 4. 设置根节点
        self.root = current_level[0] if current_level else None

    def get_merkle_root(self) -> Optional[str]:
        """获取Merkle根哈希"""
        return self.root.hash_value if self.root else None

    def get_merkle_proof(self, tx_hash: str) -> Optional[MerkleProof]:
        """
        获取交易的Merkle证明

        Args:
            tx_hash: 交易哈希

        Returns:
            MerkleProof: Merkle证明，如果交易不存在则返回None
        """
        if tx_hash not in self.transactions:
            return None

        # 找到目标叶子节点
        target_leaf = None
        for leaf in self.leaves:
            if leaf.data == tx_hash:
                target_leaf = leaf
                break

        if not target_leaf:
            return None

        # 构建证明路径
        proof_hashes = []
        proof_directions = []

        current_node = target_leaf
        self._build_proof_path(self.root, current_node, proof_hashes, proof_directions)

        return MerkleProof(
            target_hash=tx_hash,
            merkle_root=self.get_merkle_root(),
            proof_hashes=proof_hashes,
            proof_directions=proof_directions
        )

    def _build_proof_path(self, node: MerkleNode, target: MerkleNode,
                          proof_hashes: List[str], proof_directions: List[bool]) -> bool:
        """
        递归构建证明路径

        Args:
            node: 当前节点
            target: 目标节点
            proof_hashes: 证明哈希列表
            proof_directions: 证明方向列表

        Returns:
            bool: 是否找到目标节点
        """
        if node == target:
            return True

        if node.is_leaf():
            return False

        # 检查左子树
        if node.left and self._build_proof_path(node.left, target, proof_hashes, proof_directions):
            # 目标在左子树，添加右兄弟节点
            if node.right:
                proof_hashes.append(node.right.hash_value)
                proof_directions.append(True)  # 右兄弟
            return True

        # 检查右子树
        if node.right and self._build_proof_path(
                node.right, target, proof_hashes, proof_directions):
            # 目标在右子树，添加左兄弟节点
            if node.left:
                proof_hashes.append(node.left.hash_value)
                proof_directions.append(False)  # 左兄弟
            return True

        return False

    @staticmethod
    def verify_merkle_proof(proof: MerkleProof) -> bool:
        """
        验证Merkle证明

        Args:
            proof: Merkle证明

        Returns:
            bool: 证明是否有效
        """
        # 从目标交易哈希开始
        current_hash = MerkleTree._double_sha256(proof.target_hash)

        # 沿着证明路径向上计算
        for i, (sibling_hash, is_right) in enumerate(
                zip(proof.proof_hashes, proof.proof_directions)):
            if is_right:
                # 兄弟在右边
                combined = current_hash + sibling_hash
            else:
                # 兄弟在左边
                combined = sibling_hash + current_hash

            current_hash = MerkleTree._double_sha256(combined)

        # 检查是否等于Merkle根
        return current_hash == proof.merkle_root

    def get_tree_structure(self) -> Dict[str, Any]:
        """获取树结构"""
        if not self.root:
            return {}
        return self.root.to_dict()

    def get_tree_height(self) -> int:
        """获取树的高度"""
        if not self.root:
            return 0
        return self._get_node_height(self.root)

    def _get_node_height(self, node: MerkleNode) -> int:
        """获取节点高度"""
        if node.is_leaf():
            return 1

        left_height = self._get_node_height(node.left) if node.left else 0
        right_height = self._get_node_height(node.right) if node.right else 0

        return max(left_height, right_height) + 1

    def get_statistics(self) -> Dict[str, Any]:
        """获取树统计信息"""
        return {
            'transaction_count': len(self.transactions),
            'tree_height': self.get_tree_height(),
            'merkle_root': self.get_merkle_root(),
            'leaf_count': len(self.leaves)
        }

    @staticmethod
    def _double_sha256(data: str) -> str:
        """双重SHA256哈希（比特币标准）"""
        first_hash = hashlib.sha256(data.encode('utf-8')).digest()
        second_hash = hashlib.sha256(first_hash).digest()
        return second_hash.hex()

    def save_to_file(self, filename: str):
        """保存到文件"""
        data = {
            'transactions': self.transactions,
            'merkle_root': self.get_merkle_root(),
            'tree_structure': self.get_tree_structure(),
            'statistics': self.get_statistics()
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filename: str):
        """从文件加载"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.transactions = data['transactions']
        self.build_tree()


class SPVClient:
    """简化支付验证(SPV)客户端"""

    def __init__(self):
        """初始化SPV客户端"""
        self.block_headers: Dict[str, Dict] = {}  # 区块头缓存
        self.merkle_proofs: Dict[str, MerkleProof] = {}  # Merkle证明缓存

    def add_block_header(self, block_hash: str, merkle_root: str,
                         block_height: int, timestamp: int):
        """添加区块头"""
        self.block_headers[block_hash] = {
            'merkle_root': merkle_root,
            'block_height': block_height,
            'timestamp': timestamp
        }

    def verify_transaction_inclusion(self, tx_hash: str, block_hash: str,
                                     merkle_proof: MerkleProof) -> bool:
        """
        验证交易是否包含在指定区块中

        Args:
            tx_hash: 交易哈希
            block_hash: 区块哈希
            merkle_proof: Merkle证明

        Returns:
            bool: 验证结果
        """
        # 1. 检查区块头是否存在
        if block_hash not in self.block_headers:
            return False

        block_header = self.block_headers[block_hash]

        # 2. 检查Merkle根是否匹配
        if merkle_proof.merkle_root != block_header['merkle_root']:
            return False

        # 3. 验证Merkle证明
        if not MerkleTree.verify_merkle_proof(merkle_proof):
            return False

        # 4. 检查目标交易哈希是否匹配
        if merkle_proof.target_hash != tx_hash:
            return False

        return True

    def get_spv_statistics(self) -> Dict[str, Any]:
        """获取SPV统计信息"""
        return {
            'cached_block_headers': len(self.block_headers),
            'cached_merkle_proofs': len(self.merkle_proofs),
            'latest_block_height': max([h['block_height'] for h in self.block_headers.values()])
            if self.block_headers else 0
        }
