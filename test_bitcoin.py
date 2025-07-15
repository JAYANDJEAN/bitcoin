#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitcoin核心功能使用示例
展示所有核心功能的使用方法，包括：
- 基础区块链功能
- Merkle树验证
- P2P网络模拟
- 动态难度调整
"""

import bitcoin
import time


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)


def print_subsection(title: str):
    """打印子章节标题"""
    print(f"\n{title}")
    print("-" * 40)


def demo_basic_features():

    def print_balance_and_utxos(blockchain, wallets):
        print(f"区块高度：{blockchain.get_latest_block().index}")
        print(f"各地址余额、各地址UTXO详情:")
        total_balance = 0
        for name in wallets:
            balance = blockchain.get_balance(wallets[name].address)
            utxos = blockchain.get_utxos_by_address(wallets[name].address)
            total_balance += balance
            print(f"  {name}: {balance} BTC, UTXO数量: {len(utxos)}")
        print(f"总余额: {total_balance} BTC, "
              f"挖矿总奖励: {blockchain.get_latest_block().index * blockchain.mining_reward} BTC")
        # print(f"\nUTXO总数: {len(blockchain.utxo_set.utxos)}, 包括一个创世区块的挖矿奖励")
        # print(f"所有UTXO详细信息:")
        # for utxo_id, utxo in blockchain.utxo_set.utxos.items():
        #     print(f"  UTXO ID: {utxo_id}")
        #     print(f"    地址: {utxo.recipient_address}")
        #     print(f"    金额: {utxo.amount} BTC")
        #     print(f"    来自交易: {utxo.transaction_id[:16]}...")
        #     print(f"    输出索引: {utxo.output_index}")
        #     print(f"    是否已花费: {utxo.is_spent}")
        #     print(f"    ----")

    """演示基础功能"""
    # 1. 初始化系统
    print_section("1. 系统初始化")

    # 创建钱包管理器和区块链
    wallet_manager = bitcoin.WalletManager()
    blockchain = bitcoin.create_blockchain(difficulty=3, mining_reward=50.0)
    print(f"挖矿难度: {blockchain.difficulty}")
    print(f"挖矿奖励: {blockchain.mining_reward} BTC")

    # 2. 创建钱包
    print_section("2. 创建钱包")

    # 创建三个钱包
    wallet_manager.create_wallet("Alice")
    wallet_manager.create_wallet("Bob")
    wallet_manager.create_wallet("Charlie")
    wallets = wallet_manager.wallets
    print(f"钱包管理器中共有 {len(wallets)} 个钱包")
    for name in wallets:
        print(f"钱包名称: {name}, 地址: {wallets[name].address}")

    # 3. 初始挖矿 - 给Alice一些初始资金
    print_section("3. 初始挖矿")
    print_subsection("Alice获得挖矿奖励")
    # 挖几个区块给Alice获得初始资金
    for i in range(3):
        block = blockchain.mine_pending_transactions(wallets['Alice'].address)
        if block:
            print(f"区块 #{block.index} 挖矿成功")
            print(f"获得挖矿奖励: {blockchain.mining_reward} BTC")

    # 4. 查看初始状态
    print_section("4. 查看初始状态")
    # 获取所有人的余额和UTXO
    print_balance_and_utxos(blockchain, wallets)

    # 5. 创建UTXO交易
    print_section("5. 多方交易测试")
    print_subsection("Alice向Bob转账50 BTC")

    # 使用UTXO交易方法
    tx1 = blockchain.create_utxo_transaction(
        from_address=wallets['Alice'].address,
        to_address=wallets['Bob'].address,
        amount=50.0,
        fee=1.0,
        wallet=wallets['Alice']
    )

    if tx1:
        print(f"交易创建成功: {tx1.transaction_id[:16]}...")
        print(f"输入数量: {len(tx1.inputs)}, 输出数量: {len(tx1.outputs)}")
        is_signed = all(inp.signature for inp in tx1.inputs) if tx1.inputs else True
        print(f"交易已签名: {'是' if is_signed else '否'}")
        # 验证交易
        if tx1.is_valid(blockchain.utxo_set):
            print("交易验证通过")
        else:
            print("交易验证失败")

        # 添加到交易池
        blockchain.add_transaction(tx1)
    else:
        print("交易创建失败 - 可能余额不足或其他错误")

    print_subsection("Alice向Charlie转账25 BTC")

    tx2 = blockchain.create_utxo_transaction(
        from_address=wallets['Alice'].address,
        to_address=wallets['Charlie'].address,
        amount=25.0,
        fee=1.0,
        wallet=wallets['Alice']
    )

    if tx2:
        print(f"交易创建成功: {tx2.transaction_id[:16]}...")
        blockchain.add_transaction(tx2)
    else:
        print("交易创建失败 - 可能余额不足或其他错误")

    print_subsection("Bob向Charlie转账50 BTC")

    tx3 = blockchain.create_utxo_transaction(
        from_address=wallets['Bob'].address,
        to_address=wallets['Charlie'].address,
        amount=50.0,
        fee=1.0,
        wallet=wallets['Bob']
    )

    if tx3:
        print(f"交易创建成功: {tx3.transaction_id[:16]}...")
        blockchain.add_transaction(tx3)
    else:
        print("交易创建失败 - 可能余额不足或其他错误")

    # 6. 挖矿确认交易
    print_section("6. 挖矿确认交易")

    print_subsection("通过工作量证明, Charlie获得挖矿奖励")
    print(f"待处理交易数量: {len(blockchain.pending_transactions)}")

    block = blockchain.mine_pending_transactions(wallets['Charlie'].address)

    if block:
        print(f"区块 #{block.index} 挖矿成功")
        print(f"包含 {len(block.transactions)} 笔交易")
        print(f"区块哈希: {block.hash[:20]}...")

    # 7. 查看交易后状态
    print_section("7. 查看交易后状态")

    # 获取所有人的余额和UTXO
    print_balance_and_utxos(blockchain, wallets)

    # 8. 多方交易测试
    print_section("8. 再次多方交易测试")

    print_subsection("Charlie向Alice和Bob各转50 BTC")

    # 使用Charlie向Alice转50 BTC
    tx4 = blockchain.create_utxo_transaction(
        from_address=wallets['Charlie'].address,
        to_address=wallets['Alice'].address,
        amount=50.0,
        fee=1.0,
        wallet=wallets['Charlie']
    )

    if tx4:
        print(f"交易4创建成功: {tx4.transaction_id[:16]}...")
        blockchain.add_transaction(tx4)
    else:
        print("交易4创建失败 - Charlie向Alice转账失败")

    # Charlie向Bob转50 BTC（在第一笔交易添加后创建）
    tx5 = blockchain.create_utxo_transaction(
        from_address=wallets['Charlie'].address,
        to_address=wallets['Bob'].address,
        amount=50.0,
        fee=1.0,
        wallet=wallets['Charlie']
    )

    if tx5:
        print(f"交易5创建成功: {tx5.transaction_id[:16]}...")
        blockchain.add_transaction(tx5)
    else:
        print("交易5创建失败 - Charlie向Bob转账失败")

    # 挖矿确认
    print_subsection("通过工作量证明, Alice获得挖矿奖励")
    block = blockchain.mine_pending_transactions(wallets['Alice'].address)
    if block:
        print(f"区块 #{block.index} 挖矿成功")
        print(f"包含 {len(block.transactions)} 笔交易")

    print_section("9. 查看交易后状态")
    print_balance_and_utxos(blockchain, wallets)

    # 11. 完整交易历史
    print_section("10. 交易历史查询")

    # 查看Alice的交易历史
    alice_history = blockchain.get_transaction_history(wallets['Alice'].address)
    print(f"Alice的完整交易历史 ({len(alice_history)} 笔交易):")
    print()

    if not alice_history:
        print("  📭 暂无交易记录")
    else:
        # 按区块索引排序
        sorted_history = sorted(alice_history, key=lambda x: x['block_index'])

        # 累积余额计算
        running_balance = 0.0

        for i, tx_record in enumerate(sorted_history):
            # 计算净变化
            net_change = tx_record['received_amount'] - tx_record['sent_amount']
            running_balance += net_change

            # 根据交易类型选择图标
            if tx_record['type'] == 'received':
                if tx_record['is_coinbase']:
                    icon = "🎉"
                    type_desc = "挖矿奖励"
                elif tx_record['from_address'] == wallets['Alice'].address:
                    icon = "🔄"
                    type_desc = "找零"
                else:
                    icon = "📥"
                    type_desc = "收到转账"
            elif tx_record['type'] == 'sent':
                icon = "📤"
                type_desc = "发送转账"
            else:
                icon = "🔄"
                type_desc = "内部转账"

            print(f"  {i+1:2d}. {icon} 区块#{tx_record['block_index']} - {type_desc}")
            print(f"       交易ID: {tx_record['transaction_id'][:20]}...")

            # 显示发送和接收金额
            if tx_record['sent_amount'] > 0:
                print(f"       发送金额: {tx_record['sent_amount']:.1f} BTC")
            if tx_record['received_amount'] > 0:
                print(f"       接收金额: {tx_record['received_amount']:.1f} BTC")

            # 显示净变化和余额
            if net_change > 0:
                print(f"       净变化: +{net_change:.1f} BTC ✅")
            elif net_change < 0:
                print(f"       净变化: {net_change:.1f} BTC ❌")
            else:
                print(f"       净变化: {net_change:.1f} BTC 💫")

            print(f"       累积余额: {running_balance:.1f} BTC")
            print()

        # 显示汇总信息
        print("=" * 50)
        total_received = sum(tx['received_amount'] for tx in alice_history)
        total_sent = sum(tx['sent_amount'] for tx in alice_history)
        net_total = total_received - total_sent

        print(f"📊 Alice的交易汇总:")
        print(f"   总接收: {total_received:.1f} BTC")
        print(f"   总发送: {total_sent:.1f} BTC")
        print(f"   净收益: {net_total:.1f} BTC")
        print(f"   当前余额: {blockchain.get_balance(wallets['Alice'].address):.1f} BTC")
        print(f"   交易次数: {len(alice_history)} 笔")

        # 交易类型统计
        type_stats = {}
        for tx in alice_history:
            tx_type = tx['type']
            if tx_type not in type_stats:
                type_stats[tx_type] = {'count': 0, 'total_amount': 0}
            type_stats[tx_type]['count'] += 1
            type_stats[tx_type]['total_amount'] += tx['received_amount'] - tx['sent_amount']

        print(f"   交易类型分布:")
        for tx_type, stats in type_stats.items():
            print(f"     {tx_type}: {stats['count']} 笔, 净额: {stats['total_amount']:.1f} BTC")

    # 12. 系统统计信息
    print_section("11. 系统统计信息")
    bitcoin.BlockchainDisplay.print_chain_status(blockchain)


def demo_merkle_tree():
    """演示Merkle树功能"""
    print_section("Merkle树功能演示")

    # 创建测试交易哈希
    tx_hashes = [
        "tx_hash_1_alice_to_bob",
        "tx_hash_2_bob_to_charlie",
        "tx_hash_3_charlie_to_david",
        "tx_hash_4_david_to_eve"
    ]

    # 构建Merkle树
    merkle_tree = bitcoin.MerkleTree(tx_hashes)
    print(f"Merkle树构建完成")
    print(f"Merkle根: {merkle_tree.get_merkle_root()}")

    # 获取统计信息
    stats = merkle_tree.get_statistics()
    print(f"树高度: {stats['tree_height']}")
    print(f"交易数量: {stats['transaction_count']}")
    print(f"叶子节点: {stats['leaf_count']}")

    # 生成和验证Merkle证明
    target_tx = "tx_hash_2_bob_to_charlie"
    proof = merkle_tree.get_merkle_proof(target_tx)

    if proof:
        print(f"\n为交易 {target_tx} 生成Merkle证明")
        print(f"证明路径长度: {len(proof.proof_hashes)}")
        print(f"证明路径: {' -> '.join(proof.proof_hashes[:2])}...")

        # 验证证明
        is_valid = bitcoin.MerkleTree.verify_merkle_proof(proof)
        print(f"证明验证: {'通过' if is_valid else '失败'}")

        # SPV客户端演示
    print(f"\nSPV客户端演示")
    spv_client = bitcoin.SPVClient()

    # 模拟添加区块头
    block_hash = "block_hash_1"
    spv_client.add_block_header(
        block_hash=block_hash,
        merkle_root=merkle_tree.get_merkle_root(),
        block_height=1,
        timestamp=int(time.time())
    )
    print(f"添加区块头: 哈希 {block_hash}")

    # 验证交易包含性
    if spv_client.verify_transaction_inclusion(target_tx, block_hash, proof):
        print(f"SPV验证: 交易确实包含在区块中")
    else:
        print(f"SPV验证: 交易不在区块中")


def demo_network_features():
    """演示网络功能"""
    print_section("P2P网络功能演示")

    # 创建分布式网络
    network = bitcoin.create_distributed_network(difficulty=5, mining_reward=50.0)
    print(f"分布式网络创建完成")

    # 添加网络节点
    alice_node = network.add_node("Alice")
    bob_node = network.add_node("Bob")
    charlie_node = network.add_node("Charlie")

    print(f"网络节点: {list(network.nodes.keys())}")
    print(f"Alice连接的节点: {list(alice_node.peers.keys())}")

    # 显示初始网络状态
    print_subsection("初始网络状态")
    for node_id, node in network.nodes.items():
        status = node.get_network_status()
        print(f"  {node_id}: {status['blockchain_length']} 个区块, "
              f"{status['connected_peers']} 个连接, "
              f"余额 {status['balance']:.1f} BTC")

    # 第一轮：Alice先获得一些资金
    print_subsection("Alice先挖矿获得初始资金")
    alice_block = alice_node.mine_block()
    if alice_block:
        print(f"Alice挖矿成功: 区块 #{alice_block['index']}")
        alice_balance = alice_node.blockchain.get_balance(alice_node.mining_address)
        print(f"Alice获得挖矿奖励: {alice_balance} BTC")

    # 创建一些交易供挖矿竞争
    print_subsection("创建竞争交易池")

    # Alice向Bob转账
    tx1 = alice_node.blockchain.create_utxo_transaction(
        from_address=alice_node.mining_address,
        to_address=bob_node.mining_address,
        amount=10.0,
        fee=1.0,
        wallet=alice_node.wallet
    )

    if tx1:
        alice_node.broadcast_transaction(tx1)
        print(f"Alice广播转账交易: {tx1.transaction_id[:16]}...")

    # 显示交易池状态
    print(f"\n各节点待处理交易数量:")
    for node_id, node in network.nodes.items():
        pending_count = len(node.blockchain.pending_transactions)
        print(f"  {node_id}: {pending_count} 笔待处理交易")

    # 挖矿竞赛 - 模拟三个节点同时开始挖矿
    print_subsection("三节点挖矿竞赛开始！")

    import threading
    import random

    # 挖矿结果存储
    mining_results = {}
    mining_lock = threading.Lock()

    def competitive_mining(node, node_name):
        """竞争性挖矿函数"""
        try:
            # 添加随机延迟模拟真实网络延迟
            delay = random.uniform(0.1, 0.5)
            time.sleep(delay)

            print(f"  {node_name} 开始挖矿... (延迟 {delay:.2f}s)")
            start_time = time.time()

            # 尝试挖矿
            block_result = node.mine_block()

            mining_time = time.time() - start_time

            with mining_lock:
                if block_result:
                    mining_results[node_name] = {
                        'success': True,
                        'block': block_result,
                        'mining_time': mining_time,
                        'finish_time': time.time()
                    }
                    print(
                        f"  🎉 {node_name} 挖矿成功! 用时 {mining_time:.2f}s, 区块 #{block_result['index']}")
                else:
                    mining_results[node_name] = {
                        'success': False,
                        'mining_time': mining_time,
                        'finish_time': time.time()
                    }
                    print(f"  ❌ {node_name} 挖矿失败, 用时 {mining_time:.2f}s")
        except Exception as e:
            with mining_lock:
                mining_results[node_name] = {
                    'success': False,
                    'error': str(e),
                    'finish_time': time.time()
                }
            print(f"  ⚠️ {node_name} 挖矿出错: {e}")

    # 创建挖矿线程
    threads = []
    miners = [
        (alice_node, "Alice"),
        (bob_node, "Bob"),
        (charlie_node, "Charlie")
    ]

    # 启动所有挖矿线程
    start_time = time.time()
    for node, name in miners:
        thread = threading.Thread(target=competitive_mining, args=(node, name))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join(timeout=10)  # 10秒超时

    total_time = time.time() - start_time

    # 分析挖矿结果
    print_subsection("挖矿竞赛结果分析")

    successful_miners = [(name, result) for name, result in mining_results.items()
                         if result.get('success', False)]

    if successful_miners:
        # 按完成时间排序
        successful_miners.sort(key=lambda x: x[1]['finish_time'])
        winner = successful_miners[0]

        print(f"🏆 获胜者: {winner[0]}")
        print(f"   挖矿时间: {winner[1]['mining_time']:.2f}s")
        print(f"   区块高度: #{winner[1]['block']['index']}")
        print(f"   包含交易: {len(winner[1]['block']['transactions'])} 笔")

        if len(successful_miners) > 1:
            print(f"\n其他成功的矿工:")
            for name, result in successful_miners[1:]:
                print(f"   {name}: {result['mining_time']:.2f}s")
    else:
        print("❌ 所有矿工都挖矿失败")

    print(f"\n竞赛总用时: {total_time:.2f}s")

    # 网络同步验证
    print_subsection("网络同步状态检查")

    # 检查所有节点的区块链长度
    chain_lengths = {}
    latest_blocks = {}
    for node_id, node in network.nodes.items():
        chain_length = len(node.blockchain.chain)
        latest_block = node.blockchain.get_latest_block()
        chain_lengths[node_id] = chain_length
        latest_blocks[node_id] = latest_block.hash[:16] if latest_block else "无"

        print(f"  {node_id}: {chain_length} 个区块, 最新区块: {latest_blocks[node_id]}...")

    # 检查是否所有节点同步
    unique_lengths = set(chain_lengths.values())
    unique_hashes = set(latest_blocks.values())

    if len(unique_lengths) == 1 and len(unique_hashes) == 1:
        print("✅ 所有节点已完全同步")
    else:
        print("⚠️ 节点间存在分歧，可能出现分叉")

    # 第二轮竞赛 - 连续挖矿
    print_subsection("连续挖矿竞赛 (3轮)")

    # 添加更多交易
    for i in range(5):
        test_tx = bitcoin.Transaction.create_coinbase_transaction(
            f"round2_address_{i}", 3.0)
        alice_node.broadcast_transaction(test_tx)

    round_winners = []
    for round_num in range(3):
        print(f"\n第 {round_num + 1} 轮挖矿竞赛:")

        # 重置结果
        mining_results.clear()
        threads.clear()

        # 启动新一轮挖矿
        for node, name in miners:
            thread = threading.Thread(target=competitive_mining, args=(node, name))
            threads.append(thread)
            thread.start()

        # 等待完成
        for thread in threads:
            thread.join(timeout=8)

        # 找出获胜者
        successful = [(name, result) for name, result in mining_results.items()
                      if result.get('success', False)]

        if successful:
            winner = min(successful, key=lambda x: x[1]['finish_time'])
            round_winners.append(winner[0])
            print(f"  🎉 第{round_num + 1}轮获胜者: {winner[0]}")
        else:
            print(f"  ❌ 第{round_num + 1}轮无人获胜")

    # 统计总体表现
    print_subsection("总体竞赛统计")
    if round_winners:
        from collections import Counter
        winner_counts = Counter(round_winners)

        print("各矿工获胜次数:")
        for name, count in winner_counts.most_common():
            print(f"  {name}: {count} 次")

        overall_champion = winner_counts.most_common(1)[0][0]
        print(f"\n🏆 总冠军: {overall_champion}")

    # 最终网络状态
    print_subsection("最终网络状态")
    consensus = network.get_network_consensus()
    print(f"共识状态: {'达成' if consensus['consensus'] else '未达成'}")
    print(f"最长链长度: {consensus['most_common_chain_length']}")
    print(f"在线节点: {consensus['online_nodes']}/{consensus['total_nodes']}")

    # 显示最终余额
    print(f"\n最终各节点余额:")
    for node_id, node in network.nodes.items():
        balance = node.blockchain.get_balance(node.mining_address)
        print(f"  {node_id}: {balance:.1f} BTC")

    # 网络统计信息
    print_subsection("网络性能统计")
    for node_id, node in network.nodes.items():
        status = node.get_network_status()
        print(f"{node_id} 节点:")
        print(f"  区块链长度: {status['blockchain_length']}")
        print(f"  连接节点数: {status['connected_peers']}")
        print(f"  余额: {status['balance']:.1f} BTC")
        print(f"  待处理交易: {len(node.blockchain.pending_transactions)}")

    return network


def demo_difficulty_adjustment():
    """演示难度调整功能"""
    print("\n=== 难度调整功能演示 ===")

    # 创建难度调整器
    difficulty_adjuster = bitcoin.create_difficulty_adjuster()
    print(f"难度调整器创建: 初始难度 {difficulty_adjuster.initial_difficulty}")

    # 模拟区块链挖矿历史
    print(f"\n模拟挖矿历史...")
    current_time = int(time.time())
    base_difficulty = 2.0

    # 创建一系列区块头
    for i in range(10):
        # 模拟不同的挖矿时间（有些快有些慢）
        time_variation = [300, 450, 600, 750, 900, 540, 480, 720, 660, 580][i]

        header = bitcoin.BlockHeader(
            height=i + 1,
            timestamp=current_time + i * time_variation,
            difficulty=base_difficulty,
            target=f"{'0' * 8}{'f' * 56}",
            hash_value=f"block_hash_{i+1:03d}",
            previous_hash=f"prev_hash_{i:03d}" if i > 0 else "0" * 64,
            nonce=i * 12345
        )

        difficulty_adjuster.add_block_header(header)
        print(f"  区块 #{i+1}: 挖矿时间 {time_variation}s")

    # 获取难度统计
    stats = difficulty_adjuster.get_difficulty_statistics()
    print(f"\n难度统计:")
    print(f"  总区块数: {stats['total_blocks']}")
    print(f"  当前难度: {stats['current_difficulty']:.2f}")
    print(f"  平均难度: {stats['avg_difficulty']:.2f}")
    print(f"  平均出块时间: {stats['avg_block_time']:.1f}秒")
    print(f"  目标出块时间: {stats['target_block_time']}秒")

    # 预测下一次调整
    prediction = difficulty_adjuster.predict_next_adjustment()
    if prediction:
        print(f"\n下一次难度调整预测:")
        print(f"  剩余区块数: {prediction.get('blocks_until_adjustment', 'N/A')}")
        print(f"  预计调整比例: {prediction.get('predicted_ratio', 'N/A'):.3f}")

    # 模拟网络算力变化
    print(f"\n模拟网络算力变化...")
    simulation_results = difficulty_adjuster.simulate_network_hashrate_change(
        hashrate_multiplier=1.5,  # 算力增加50%
        num_blocks=5
    )

    print(f"  模拟了 {len(simulation_results)} 个区块")
    for header in simulation_results[-3:]:  # 显示最后3个
        print(f"  区块 #{header.height}: 难度 {header.difficulty:.3f}")


def demo_integration():
    """演示完整集成功能"""
    print("\n=== 完整集成演示 ===")

    # 创建完整的比特币网络环境
    network = bitcoin.create_distributed_network(difficulty=2, mining_reward=50.0)

    # 添加多个矿工节点
    miners = []
    for i in range(3):
        miner = network.add_node(f"Miner{i+1}")
        miners.append(miner)

    print(f"矿工网络建立: {len(miners)} 个矿工节点")

    # 创建用户钱包
    user_wallet = bitcoin.create_wallet()
    merchant_wallet = bitcoin.create_wallet()

    print(f"用户钱包: {user_wallet.address[:20]}...")
    print(f"商家钱包: {merchant_wallet.address[:20]}...")

    # 矿工1挖矿获得初始资金
    print(f"\nMiner1开始挖空块...")
    block1 = miners[0].mine_block()
    if block1:
        print(f"挖矿成功: 区块 #{block1['index']}")
        print(f"Miner1余额: {miners[0].blockchain.get_balance(miners[0].mining_address)} BTC")

    # 创建用户交易
    print(f"\nMiner1向用户转账...")
    user_tx = miners[0].blockchain.create_utxo_transaction(
        miners[0].mining_address, user_wallet.address, 20.0,
        fee=1.0, wallet=miners[0].wallet
    )

    if user_tx:
        miners[0].broadcast_transaction(user_tx)
        print(f"交易广播: {user_tx.transaction_id[:20]}...")

        # 矿工2挖矿确认交易
        print(f"Miner2确认交易...")
        block2 = miners[1].mine_block()
        if block2:
            print(f"交易确认: 区块 #{block2['index']}")

    # 用户向商家付款
    print(f"\n用户向商家付款...")
    payment_tx = miners[1].blockchain.create_utxo_transaction(
        user_wallet.address, merchant_wallet.address, 5.0,
        fee=0.5, wallet=user_wallet
    )

    if payment_tx:
        miners[1].broadcast_transaction(payment_tx)
        print(f"付款交易广播: {payment_tx.transaction_id[:20]}...")

        # 矿工3确认付款
        print(f"Miner3确认付款...")
        block3 = miners[2].mine_block()
        if block3:
            print(f"付款确认: 区块 #{block3['index']}")

    # 显示最终状态
    print(f"\n最终余额:")
    for i, miner in enumerate(miners):
        balance = miner.blockchain.get_balance(miner.mining_address)
        print(f"  Miner{i+1}: {balance:.1f} BTC")

    user_balance = miners[2].blockchain.get_balance(user_wallet.address)
    merchant_balance = miners[2].blockchain.get_balance(merchant_wallet.address)
    print(f"  用户: {user_balance:.1f} BTC")
    print(f"  商家: {merchant_balance:.1f} BTC")

    # 验证Merkle证明
    latest_block = miners[2].blockchain.get_latest_block()
    if latest_block.merkle_tree and payment_tx:
        proof = latest_block.get_merkle_proof(payment_tx.transaction_id)
        if proof:
            is_valid = latest_block.verify_transaction_inclusion(payment_tx.transaction_id, proof)
            print(f"Merkle证明验证: {'通过' if is_valid else '失败'}")


def main():
    """主演示函数"""
    try:
        # 运行各个演示
        demo_basic_features()
        # demo_merkle_tree()
        # demo_network_features()
        # demo_difficulty_adjustment()
        # demo_integration()

    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
