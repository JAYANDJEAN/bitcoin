#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 区块链分布式网络模拟器
这个模块包含了模拟分布式区块链网络的相关类：
- NetworkNode: 模拟单个网络节点
- DistributedNetwork: 管理多个节点的网络
功能特性：
- P2P网络连接模拟
- 区块和交易广播
- 网络分区处理
- 节点故障恢复
- 共识算法验证
作者: Bitcoin Demo Project
版本: 1.0.1
许可: MIT License
"""
__version__ = "1.0.1"
__author__ = "Bitcoin Demo Project"

import json
import time
import random
import threading
from typing import List, Optional, Dict, Any

# 使用相对导入避免循环导入
from .wallet import Wallet
from .transaction import Transaction
from .blockchain import Blockchain
from .config import NETWORK_DELAY, DEFAULT_TRANSACTION_FEE


class NetworkNode:
    """网络节点类 - 模拟分布式账本中的单个节点"""

    def __init__(self, node_id: str, difficulty: int = 3, mining_reward: float = 50):
        """
        初始化网络节点
        Args:
            node_id: 节点唯一标识
            difficulty: 挖矿难度
            mining_reward: 挖矿奖励
        """
        self.node_id = node_id
        self.blockchain = Blockchain(difficulty, mining_reward)
        self.peers: Dict[str, 'NetworkNode'] = {}  # 连接的对等节点
        self.is_mining = False
        # 创建节点钱包
        self.wallet = Wallet()
        self.mining_address = self.wallet.address
        # 网络状态
        self.online = True
        self.network_delay = random.uniform(NETWORK_DELAY, NETWORK_DELAY * 5)  # 模拟网络延迟
        # 同步状态
        self.last_sync_time = time.time()
        self.sync_interval = 10  # 同步间隔（秒）

    def connect_peer(self, peer: 'NetworkNode') -> None:
        """连接到其他节点"""
        if peer.node_id != self.node_id and peer.node_id not in self.peers:
            self.peers[peer.node_id] = peer
            peer.peers[self.node_id] = self

    def disconnect_peer(self, peer_id: str) -> None:
        """断开与指定节点的连接"""
        if peer_id in self.peers:
            peer = self.peers[peer_id]
            del self.peers[peer_id]
            if self.node_id in peer.peers:
                del peer.peers[self.node_id]

    def broadcast_transaction(self, transaction: Transaction) -> None:
        """广播交易到网络中的其他节点"""
        if not self.online:
            return
        # 添加到自己的交易池
        self.blockchain.add_transaction(transaction)
        # 广播给其他节点
        for peer_id, peer in self.peers.items():
            if peer.online:
                # 模拟网络延迟
                time.sleep(self.network_delay)
                peer._receive_transaction(transaction, from_node=self.node_id)

    def _receive_transaction(self, transaction: Transaction, from_node: str) -> None:
        """接收其他节点广播的交易"""
        if not self.online:
            return
        # 验证交易并添加到待处理池
        if self.blockchain.add_transaction(transaction):
            print(f"📨 节点 {self.node_id} 接收到来自 {from_node} 的交易: {transaction.transaction_id[:8]}...")

    def mine_block(self) -> Optional[dict]:
        """挖矿并广播新区块"""
        if not self.online or self.is_mining:
            return None
        # 即使没有待处理交易，也可以挖矿获得奖励
        if len(self.blockchain.pending_transactions) == 0:
            print(f"⛏️  节点 {self.node_id} 开始挖空块（仅奖励）")
        self.is_mining = True
        try:
            # 挖矿
            new_block = self.blockchain.mine_pending_transactions(self.mining_address)
            # 广播新区块
            self._broadcast_block(new_block)
            return new_block.to_dict()
        finally:
            self.is_mining = False

    def _broadcast_block(self, block) -> None:
        """广播新挖出的区块"""
        if not self.online:
            return
        for peer_id, peer in self.peers.items():
            if peer.online:
                # 模拟网络延迟
                time.sleep(self.network_delay)
                peer._receive_block(block, from_node=self.node_id)

    def _receive_block(self, block, from_node: str) -> None:
        """接收其他节点广播的区块"""
        if not self.online:
            return
        # 检查区块是否为None
        if block is None:
            return
        # 验证区块
        if self._validate_received_block(block):
            # 如果是有效区块，检查是否需要更新本地链
            if block.index == len(self.blockchain.chain):
                # 新区块直接添加到链末尾
                self.blockchain.chain.append(block)
                # 更新UTXO集合
                block_transactions = []
                for tx_data in block.transactions:
                    transaction = Transaction.from_dict(tx_data)
                    block_transactions.append(transaction)
                self.blockchain._update_utxo_set(block_transactions)
                # 移除已处理的交易
                self._remove_processed_transactions(block.transactions)
            elif block.index < len(self.blockchain.chain):
                # 收到的是较旧的区块，忽略
                print(f"🕰️ 节点 {self.node_id} 收到旧区块 #{block.index}，忽略")
            else:
                # 收到的区块索引超前，可能需要同步
                self.request_blockchain_sync()

    def _validate_received_block(self, block) -> bool:
        """验证接收到的区块"""
        # 基本验证
        if not hasattr(block, 'hash') or not hasattr(block, 'previous_hash'):
            return False
        # 验证哈希值
        calculated_hash = block.calculate_hash()
        if calculated_hash != block.hash:
            return False
        # 验证前置哈希（如果不是第一个区块）
        if block.index > 0:
            latest_block = self.blockchain.get_latest_block()
            if block.previous_hash != latest_block.hash:
                return False
        return True

    def _remove_processed_transactions(self, transactions: List[Dict]) -> None:
        """移除已被处理的交易"""
        processed_tx_ids = {tx.get('transaction_id')
                            for tx in transactions if 'transaction_id' in tx}

        # 过滤待处理交易
        filtered_transactions = []
        for tx in self.blockchain.pending_transactions:
            tx_id = None
            if isinstance(tx, Transaction):
                tx_id = tx.transaction_id
            elif isinstance(tx, dict) and 'transaction_id' in tx:
                tx_id = tx['transaction_id']

            if tx_id and tx_id not in processed_tx_ids:
                filtered_transactions.append(tx)

        self.blockchain.pending_transactions = filtered_transactions

    def request_blockchain_sync(self) -> None:
        """请求与网络同步区块链"""
        if not self.online or not self.peers:
            return
        # 找到最长的链
        longest_chain = self.blockchain.chain
        longest_chain_node = None
        for peer_id, peer in self.peers.items():
            if peer.online and len(peer.blockchain.chain) > len(longest_chain):
                longest_chain = peer.blockchain.chain
                longest_chain_node = peer_id
        # 如果找到更长的链，进行同步
        if longest_chain_node and len(longest_chain) > len(self.blockchain.chain):
            self._sync_with_peer(longest_chain_node)

    def _sync_with_peer(self, peer_id: str) -> None:
        """与指定节点同步"""
        if peer_id not in self.peers:
            return
        peer = self.peers[peer_id]
        if not peer.online:
            return
        # 验证对方的链
        if peer.blockchain.is_chain_valid():
            print(f"🔄 节点 {self.node_id} 正在与 {peer_id} 同步区块链")
            # 备份当前状态
            old_chain_length = len(self.blockchain.chain)
            # 采用最长链
            self.blockchain.chain = [block for block in peer.blockchain.chain]
            # 重新计算UTXO集合（重建整个UTXO集合）
            self.blockchain.utxo_set.utxos = {}
            for block in self.blockchain.chain:
                for tx_data in block.transactions:
                    transaction = Transaction.from_dict(tx_data)
                    self.blockchain.utxo_set.update_from_transaction(transaction)
            # 清空与新链冲突的待处理交易
            self._clean_conflicting_transactions()
        else:
            print(f"❌ 节点 {peer_id} 的区块链无效，同步失败")

    def _clean_conflicting_transactions(self) -> None:
        """清理与当前链冲突的待处理交易"""
        valid_transactions = []
        for tx in self.blockchain.pending_transactions:
            # 检查交易是否仍然有效
            if isinstance(tx, Transaction):
                if tx.is_valid(self.blockchain.utxo_set):
                    valid_transactions.append(tx)
            else:
                # 如果是字典格式，尝试转换
                try:
                    transaction = Transaction.from_dict(tx)
                    if transaction.is_valid(self.blockchain.utxo_set):
                        valid_transactions.append(transaction)
                except Exception:
                    continue
        self.blockchain.pending_transactions = valid_transactions

    def go_offline(self) -> None:
        """模拟节点离线"""
        self.online = False

    def go_online(self) -> None:
        """模拟节点上线"""
        self.online = True
        # 上线后立即尝试同步
        self.request_blockchain_sync()

    def get_network_status(self) -> Dict:
        """获取网络状态信息"""
        return {
            "node_id": self.node_id,
            "online": self.online,
            "blockchain_length": len(self.blockchain.chain),
            "pending_transactions": len(self.blockchain.pending_transactions),
            "connected_peers": len(self.peers),
            "peer_list": list(self.peers.keys()),
            "mining_address": self.mining_address,
            "balance": self.blockchain.get_balance(self.mining_address),
            "is_mining": self.is_mining
        }

    def __str__(self) -> str:
        """节点的字符串表示"""
        status = "在线" if self.online else "离线"
        return f"节点 {self.node_id} ({status}) - {len(self.blockchain.chain)} 个区块"


class DistributedNetwork:
    """分布式网络管理器 - 管理多个区块链节点"""

    def __init__(self, difficulty: int = 3, mining_reward: float = 50):
        """
        初始化分布式网络
        Args:
            difficulty: 全网挖矿难度
            mining_reward: 挖矿奖励
        """
        self.nodes: Dict[str, NetworkNode] = {}
        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self.network_topology = "mesh"  # 网络拓扑：mesh(网状) 或 star(星状)

    def add_node(self, node_id: str) -> NetworkNode:
        """添加新节点到网络"""
        if node_id in self.nodes:
            return self.nodes[node_id]
        node = NetworkNode(node_id, self.difficulty, self.mining_reward)
        self.nodes[node_id] = node
        # 根据网络拓扑连接节点
        self._connect_new_node(node)
        return node

    def _connect_new_node(self, new_node: NetworkNode) -> None:
        """根据网络拓扑连接新节点"""
        if self.network_topology == "mesh":
            # 网状网络：与所有现有节点连接
            for existing_node in self.nodes.values():
                if existing_node.node_id != new_node.node_id:
                    new_node.connect_peer(existing_node)
        elif self.network_topology == "star":
            # 星状网络：只与第一个节点（中心节点）连接
            if len(self.nodes) > 1:
                center_node = list(self.nodes.values())[0]
                new_node.connect_peer(center_node)

    def remove_node(self, node_id: str) -> bool:
        """从网络中移除节点"""
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        # 断开所有连接
        peer_ids = list(node.peers.keys())
        for peer_id in peer_ids:
            node.disconnect_peer(peer_id)
        del self.nodes[node_id]
        return True

    def broadcast_transaction(self, from_node_id: str, to_address: str, amount: float) -> bool:
        """通过指定节点广播交易"""
        if from_node_id not in self.nodes:
            return False
        node = self.nodes[from_node_id]
        if not node.online:
            return False
        # 创建交易
        from_address = node.mining_address
        transaction = node.blockchain.create_utxo_transaction(
            from_address, to_address, amount, wallet=node.wallet
        )
        if not transaction:
            return False
        # 广播交易
        node.broadcast_transaction(transaction)
        return True

    def start_mining_competition(self, duration: int = 30) -> Dict[str, int]:
        """启动挖矿竞赛"""
        mining_results = {node_id: 0 for node_id in self.nodes.keys()}

        def mine_worker(node: NetworkNode):
            """挖矿工作线程"""
            end_time = time.time() + duration
            while time.time() < end_time and node.online:
                result = node.mine_block()
                if result:
                    mining_results[node.node_id] += 1
                time.sleep(0.1)  # 短暂休息

        # 启动所有节点的挖矿线程
        threads = []
        for node in self.nodes.values():
            if node.online:
                thread = threading.Thread(target=mine_worker, args=(node,))
                threads.append(thread)
                thread.start()

        # 等待所有线程完成
        time.sleep(duration)
        for thread in threads:
            thread.join(timeout=1)
        return mining_results

    def simulate_network_partition(self, group1_nodes: List[str], group2_nodes: List[str]) -> None:
        """模拟网络分区"""
        # 断开两组节点之间的连接
        for node_id1 in group1_nodes:
            if node_id1 in self.nodes:
                node1 = self.nodes[node_id1]
                for node_id2 in group2_nodes:
                    if node_id2 in node1.peers:
                        node1.disconnect_peer(node_id2)

    def heal_network_partition(self) -> None:
        """修复网络分区"""
        # 重新建立连接
        node_list = list(self.nodes.values())
        for i, node1 in enumerate(node_list):
            for node2 in node_list[i + 1:]:
                if node2.node_id not in node1.peers:
                    node1.connect_peer(node2)
        # 触发同步
        for node in self.nodes.values():
            if node.online:
                node.request_blockchain_sync()

    def simulate_node_failures(self, failure_rate: float = 0.3) -> List[str]:
        """模拟节点故障"""
        failed_nodes = []
        for node_id, node in self.nodes.items():
            if random.random() < failure_rate and node.online:
                node.go_offline()
                failed_nodes.append(node_id)
        return failed_nodes

    def recover_failed_nodes(self, failed_nodes: List[str]) -> None:
        """恢复故障节点"""
        for node_id in failed_nodes:
            if node_id in self.nodes:
                self.nodes[node_id].go_online()

    def get_network_consensus(self) -> Dict:
        """获取网络共识状态"""
        online_nodes = [node for node in self.nodes.values() if node.online]
        if not online_nodes:
            return {"consensus": False, "reason": "没有在线节点"}

        # 检查链长度一致性
        chain_lengths = [len(node.blockchain.chain) for node in online_nodes]
        most_common_length = max(set(chain_lengths), key=chain_lengths.count)
        consensus_ratio = chain_lengths.count(most_common_length) / len(chain_lengths)

        # 检查最新区块哈希一致性
        latest_hashes = []
        for node in online_nodes:
            if len(node.blockchain.chain) > 0:
                latest_hashes.append(node.blockchain.chain[-1].hash)
        hash_consensus = len(set(latest_hashes)) == 1 if latest_hashes else True

        return {
            "consensus": consensus_ratio >= 0.51 and hash_consensus,
            "chain_length_consensus_ratio": consensus_ratio,
            "most_common_chain_length": most_common_length,
            "hash_consensus": hash_consensus,
            "online_nodes": len(online_nodes),
            "total_nodes": len(self.nodes)
        }

    def display_network_status(self) -> None:
        """显示网络状态"""
        print("\n=== 🌐 分布式网络状态 ===")
        # 网络概览
        online_count = sum(1 for node in self.nodes.values() if node.online)
        print(f"网络节点: {online_count}/{len(self.nodes)} 在线")
        print(f"网络拓扑: {self.network_topology}")
        print(f"挖矿难度: {self.difficulty}")
        print(f"挖矿奖励: {self.mining_reward} BTC")

        # 共识状态
        consensus = self.get_network_consensus()
        consensus_status = "✅ 达成共识" if consensus["consensus"] else "❌ 未达成共识"
        print(f"网络共识: {consensus_status}")
        if not consensus["consensus"]:
            print(f"  链长度共识率: {consensus['chain_length_consensus_ratio']:.1%}")
            print(f"  哈希共识: {'是' if consensus['hash_consensus'] else '否'}")

        # 节点详情
        print("\n=== 📊 节点详情 ===")
        for node_id, node in self.nodes.items():
            status = node.get_network_status()
            online_indicator = "🟢" if status["online"] else "🔴"
            if status["connected_peers"] > 0:
                peers_str = ', '.join(status["peer_list"])
                print(
                    f"  {online_indicator} {node_id}: {status['blockchain_length']}块, {status['balance']:.2f}BTC, 连接: {peers_str}")
            else:
                print(
                    f"  {online_indicator} {node_id}: {status['blockchain_length']}块, {status['balance']:.2f}BTC, 无连接")

    def save_network_state(self, filename: str) -> None:
        """保存网络状态到文件"""
        network_data = {
            "network_info": {
                "total_nodes": len(self.nodes),
                "difficulty": self.difficulty,
                "mining_reward": self.mining_reward,
                "topology": self.network_topology
            },
            "nodes": {}
        }
        for node_id, node in self.nodes.items():
            network_data["nodes"][node_id] = {
                "status": node.get_network_status(),
                "blockchain": node.blockchain.to_dict()
            }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(network_data, f, indent=2, ensure_ascii=False)
            print(f"💾 网络状态已保存到 {filename}")
        except Exception as e:
            print(f"❌ 保存网络状态失败: {e}")

    def __str__(self) -> str:
        """网络的字符串表示"""
        online_count = sum(1 for node in self.nodes.values() if node.online)
        return f"分布式网络 - {online_count}/{len(self.nodes)} 节点在线"
