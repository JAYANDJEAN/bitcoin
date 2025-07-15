#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 比特币系统前端展示应用
基于Flask的Web界面，提供区块链浏览器、钱包管理、交易功能
"""

import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS

from bitcoin.blockchain import Blockchain
from bitcoin.wallet import Wallet, WalletManager
from bitcoin.transaction import Transaction
from bitcoin.config import DEFAULT_DIFFICULTY, DEFAULT_MINING_REWARD, DEFAULT_TRANSACTION_FEE, config

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用环境变量
CORS(app)

# 全局变量
blockchain = Blockchain()
wallet_manager = WalletManager()
mining_thread = None
mining_active = False

# 挖矿轮次状态跟踪
mining_round_active = False
mining_round_data = {
    'round_number': 0,
    'participants': [],
    'winner': None,
    'start_time': 0,
    'block_ready': False,
    'round_complete': False,
    'computing_time': 10.0  # 每轮计算时间（秒）
}

# 工具函数


def format_datetime(timestamp):
    """格式化时间戳为可读格式"""
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except BaseException:
        return timestamp


def truncate_hash(hash_str, length=16):
    """截断哈希值显示"""
    return f"{hash_str[:length]}..." if len(hash_str) > length else hash_str


# 添加模板过滤器
app.jinja_env.filters['format_datetime'] = format_datetime
app.jinja_env.filters['truncate_hash'] = truncate_hash

# 主页面路由


@app.route('/')
def index():
    """主页 - 区块链浏览器"""
    try:
        chain_info = {
            'height': len(blockchain.chain),
            'difficulty': blockchain.difficulty,
            'pending_transactions': len(blockchain.pending_transactions),
            'total_supply': sum(blockchain.get_balance(address) for address in set(
                out['recipient_address'] for block in blockchain.chain for tx in block.transactions
                for out in tx.get('outputs', [])
                if out.get('recipient_address')
            ))
        }

        # 获取最新的5个区块
        latest_blocks = blockchain.chain[-5:][::-1]  # 反转顺序，最新的在前

        # 获取最新的交易
        latest_transactions = []
        for block in reversed(blockchain.chain[-10:]):  # 最新的10个区块
            for tx in block.transactions:
                # 判断是否为coinbase交易
                is_coinbase = not tx.get('inputs') or not tx.get(
                    'inputs', [{}])[0].get('transaction_id')

                # 获取发送方信息
                if is_coinbase:
                    if block.index == 0:
                        from_address = 'Genesis'
                    else:
                        from_address = '系统 (挖矿奖励)'
                else:
                    from_address = tx.get('inputs', [{}])[0].get('transaction_id', 'N/A')

                # 获取接收方信息
                to_address = tx.get('outputs', [{}])[0].get(
                    'recipient_address', 'N/A') if tx.get('outputs') else 'N/A'

                latest_transactions.append({
                    'transaction_id': tx.get('transaction_id', 'N/A'),
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount': tx.get('outputs', [{}])[0].get('amount', 0) if tx.get('outputs') else 0,
                    'timestamp': block.timestamp,
                    'block_index': block.index,
                    'is_coinbase': is_coinbase
                })
            if len(latest_transactions) >= 10:
                break

        return render_template('index.html',
                               chain_info=chain_info,
                               latest_blocks=latest_blocks,
                               latest_transactions=latest_transactions)
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return render_template(
            'index.html',
            chain_info={
                'height': 0,
                'difficulty': 0,
                'pending_transactions': 0,
                'total_supply': 0},
            latest_blocks=[],
            latest_transactions=[])


@app.route('/blocks')
def blocks():
    """区块列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10

        total_blocks = len(blockchain.chain)
        start_idx = max(0, total_blocks - (page * per_page))
        end_idx = max(0, total_blocks - ((page - 1) * per_page))

        blocks_data = blockchain.chain[start_idx:end_idx][::-1]  # 反转顺序

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_blocks,
            'has_prev': page > 1,
            'has_next': start_idx > 0,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if start_idx > 0 else None
        }

        return render_template('blocks.html', blocks=blocks_data, pagination=pagination)
    except Exception as e:
        app.logger.error(f"Error in blocks route: {str(e)}")
        return render_template('blocks.html', blocks=[], pagination={})


@app.route('/block/<int:block_index>')
def block_detail(block_index):
    """区块详情页面"""
    try:
        if 0 <= block_index < len(blockchain.chain):
            block = blockchain.chain[block_index]
            chain_length = len(blockchain.chain)
            return render_template('block_detail.html', block=block, chain_length=chain_length)
        else:
            flash('区块不存在', 'error')
            return redirect(url_for('blocks'))
    except Exception as e:
        app.logger.error(f"Error in block_detail route: {str(e)}")
        flash('获取区块详情失败', 'error')
        return redirect(url_for('blocks'))


@app.route('/wallets')
def wallets():
    """钱包管理页面"""
    try:
        # 获取高亮参数（用于显示获胜者）
        highlight_wallet = request.args.get('highlight', '')

        wallets_data = []
        for wallet_name, wallet in wallet_manager.wallets.items():
            balance = blockchain.get_balance(wallet.address)
            wallets_data.append({
                'name': wallet_name,
                'address': wallet.address,
                'balance': balance,
                'wallet': wallet,
                'is_winner': wallet_name == highlight_wallet  # 标记是否为获胜者
            })

        return render_template('wallets.html',
                               wallets=wallets_data,
                               highlight_wallet=highlight_wallet)
    except Exception as e:
        app.logger.error(f"Error in wallets route: {str(e)}")
        return render_template('wallets.html', wallets=[], highlight_wallet='')


@app.route('/wallet/<wallet_name>')
def wallet_detail(wallet_name):
    """钱包详情页面"""
    try:
        wallet = wallet_manager.get_wallet(wallet_name)
        if wallet:
            balance = blockchain.get_balance(wallet.address)
            # 清除缓存以确保获取最新的交易历史
            blockchain.history_cache.invalidate_cache()
            transaction_history = blockchain.get_transaction_history(wallet.address)

            # 获取UTXO信息
            utxos = blockchain.utxo_set.get_utxos_by_address(wallet.address)

            # 收集被待处理交易锁定的UTXO
            locked_utxos = set()
            for pending_tx in blockchain.pending_transactions:
                for input_tx in pending_tx.inputs:
                    locked_utxos.add(input_tx.get_utxo_id())

            utxo_info = []
            for utxo in utxos:
                utxo_id = utxo.get_utxo_id()
                status = 'spent' if utxo.is_spent else (
                    'locked' if utxo_id in locked_utxos else 'available')

                # 获取交易时间戳
                timestamp = None
                if utxo.transaction_id in blockchain.transaction_index:
                    block_index, tx_index = blockchain.transaction_index[utxo.transaction_id]
                    try:
                        if block_index < len(blockchain.chain):
                            block = blockchain.chain[block_index]
                            if tx_index < len(block.transactions):
                                tx_data = block.transactions[tx_index]
                                timestamp = tx_data.get('timestamp')
                    except Exception:
                        pass

                utxo_info.append({
                    'transaction_id': utxo.transaction_id,
                    'output_index': utxo.output_index,
                    'amount': utxo.amount,
                    'address': utxo.recipient_address,
                    'is_spent': utxo.is_spent,
                    'status': status,
                    'timestamp': timestamp
                })

            return render_template('wallet_detail.html',
                                   wallet=wallet,
                                   wallet_name=wallet_name,
                                   balance=balance,
                                   transaction_history=transaction_history,
                                   utxos=utxo_info)
        else:
            flash('钱包不存在', 'error')
            return redirect(url_for('wallets'))
    except Exception as e:
        app.logger.error(f"Error in wallet_detail route: {str(e)}")
        flash('获取钱包详情失败', 'error')
        return redirect(url_for('wallets'))


@app.route('/transaction')
def transaction():
    """交易页面"""
    try:
        wallets_data = []
        for wallet_name, wallet in wallet_manager.wallets.items():
            balance = blockchain.get_balance(wallet.address)
            wallets_data.append({
                'name': wallet_name,
                'address': wallet.address,
                'balance': balance
            })

        return render_template('transaction.html', wallets=wallets_data)
    except Exception as e:
        app.logger.error(f"Error in transaction route: {str(e)}")
        return render_template('transaction.html', wallets=[])


@app.route('/mining')
def mining():
    """挖矿页面"""
    try:
        wallets_data = []
        for wallet_name, wallet in wallet_manager.wallets.items():
            wallets_data.append({
                'name': wallet_name,
                'address': wallet.address
            })

        # 获取区块链信息
        chain_info = {
            'height': len(blockchain.chain),
            'difficulty': blockchain.difficulty
        }

        return render_template('mining.html',
                               wallets=wallets_data,
                               mining_active=mining_active,
                               mining_round_active=mining_round_active,
                               pending_transactions=len(blockchain.pending_transactions),
                               chain_info=chain_info)
    except Exception as e:
        app.logger.error(f"Error in mining route: {str(e)}")
        return render_template(
            'mining.html',
            wallets=[],
            mining_active=False,
            mining_round_active=False,
            pending_transactions=0,
            chain_info={'height': 0, 'difficulty': 0})


@app.route('/color_preview')
def color_preview():
    """配色预览页面"""
    return render_template('color_preview.html')

# API端点


@app.route('/api/create_wallet', methods=['POST'])
def api_create_wallet():
    """创建新钱包"""
    try:
        data = request.get_json()
        wallet_name = data.get('name')

        if not wallet_name:
            return jsonify({'error': '钱包名称不能为空'}), 400

        if wallet_name in wallet_manager.wallets:
            return jsonify({'error': '钱包名称已存在'}), 400

        wallet = wallet_manager.create_wallet(wallet_name)

        return jsonify({
            'success': True,
            'wallet': {
                'name': wallet_name,
                'address': wallet.address,
                'balance': blockchain.get_balance(wallet.address)
            }
        })
    except Exception as e:
        app.logger.error(f"Error creating wallet: {str(e)}")
        return jsonify({'error': '创建钱包失败'}), 500


@app.route('/api/import_wallet', methods=['POST'])
def api_import_wallet():
    """导入钱包"""
    try:
        data = request.get_json()
        wallet_name = data.get('name')
        private_key = data.get('private_key')

        if not wallet_name or not private_key:
            return jsonify({'error': '钱包名称和私钥不能为空'}), 400

        if wallet_name in wallet_manager.wallets:
            return jsonify({'error': '钱包名称已存在'}), 400

        wallet = wallet_manager.import_wallet(wallet_name, private_key)

        return jsonify({
            'success': True,
            'wallet': {
                'name': wallet_name,
                'address': wallet.address,
                'balance': blockchain.get_balance(wallet.address)
            }
        })
    except Exception as e:
        app.logger.error(f"Error importing wallet: {str(e)}")
        return jsonify({'error': '导入钱包失败，请检查私钥格式'}), 500


@app.route('/api/send_transaction', methods=['POST'])
def api_send_transaction():
    """发送交易"""
    try:
        data = request.get_json()
        from_wallet = data.get('from_wallet')
        to_address = data.get('to_address')
        amount = float(data.get('amount', 0))

        if not from_wallet or not to_address or amount <= 0:
            return jsonify({'error': '请填写完整的交易信息'}), 400

        wallet = wallet_manager.get_wallet(from_wallet)
        if not wallet:
            return jsonify({'error': '源钱包不存在'}), 400

        # 检查余额
        balance = blockchain.get_balance(wallet.address)
        if balance < amount + DEFAULT_TRANSACTION_FEE:
            return jsonify({'error': f'余额不足，当前余额: {balance}'}), 400

        # 创建交易
        transaction = blockchain.create_utxo_transaction(
            wallet.address, to_address, amount, DEFAULT_TRANSACTION_FEE, wallet
        )

        if transaction:
            success = blockchain.add_transaction(transaction)
            if success:
                return jsonify({
                    'success': True,
                    'transaction_id': transaction.transaction_id,
                    'message': '交易已添加到待处理池'
                })
            else:
                return jsonify({'error': '交易验证失败'}), 400
        else:
            return jsonify({'error': '创建交易失败'}), 500

    except Exception as e:
        app.logger.error(f"Error sending transaction: {str(e)}")
        return jsonify({'error': '发送交易失败'}), 500


# 旧的单一挖矿功能已被新的挖矿轮次系统替代


@app.route('/api/start_mining_round', methods=['POST'])
def api_start_mining_round():
    """开始新一轮挖矿竞争"""
    global mining_round_active, mining_round_data

    try:
        if mining_round_active:
            return jsonify({'error': '挖矿轮次已在进行中'}), 400

        # 获取所有钱包作为参与者
        participants = []
        for wallet_name, wallet in wallet_manager.wallets.items():
            participants.append({
                'name': wallet_name,
                'address': wallet.address,
                'nonce': 0,
                'computing': True
            })

        if not participants:
            return jsonify({'error': '没有可用的钱包参与挖矿'}), 400

        # 初始化新一轮挖矿
        mining_round_data['round_number'] += 1
        mining_round_data['participants'] = participants
        mining_round_data['winner'] = None
        mining_round_data['start_time'] = time.time()
        mining_round_data['block_ready'] = False
        mining_round_data['round_complete'] = False
        mining_round_active = True

        print(f"🚀 开始第 {mining_round_data['round_number']} 轮挖矿竞争")
        print(f"👥 参与者: {', '.join([p['name'] for p in participants])}")

        return jsonify({
            'success': True,
            'message': '挖矿轮次已开始',
            'round_number': mining_round_data['round_number'],
            'participants': participants
        })
    except Exception as e:
        app.logger.error(f"Error starting mining round: {str(e)}")
        return jsonify({'error': '开始挖矿轮次失败'}), 500


@app.route('/api/mining_round_status')
def api_mining_round_status():
    """获取当前挖矿轮次状态"""
    try:
        if not mining_round_active:
            return jsonify({
                'success': True,
                'round_active': False,
                'round_number': mining_round_data['round_number']
            })

        # 更新参与者的随机数
        import random
        current_time = time.time()
        elapsed_time = current_time - mining_round_data['start_time']

        # 模拟计算过程
        for participant in mining_round_data['participants']:
            if participant['computing']:
                participant['nonce'] = random.randint(1, int(elapsed_time * 1000))

        # 检查是否到达计算时间
        if elapsed_time >= mining_round_data['computing_time'] and not mining_round_data['winner']:
            # 随机选择获胜者
            winner = random.choice(mining_round_data['participants'])
            mining_round_data['winner'] = winner
            mining_round_data['block_ready'] = True

            # 停止所有参与者的计算
            for participant in mining_round_data['participants']:
                participant['computing'] = False

            print(f"🎯 第 {mining_round_data['round_number']} 轮挖矿获胜者: {winner['name']}")

        return jsonify({
            'success': True,
            'round_active': mining_round_active,
            'round_number': mining_round_data['round_number'],
            'participants': mining_round_data['participants'],
            'winner': mining_round_data['winner'],
            'block_ready': mining_round_data['block_ready'],
            'round_complete': mining_round_data['round_complete'],
            'elapsed_time': elapsed_time,
            'computing_time': mining_round_data['computing_time']
        })
    except Exception as e:
        app.logger.error(f"Error getting mining round status: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取挖矿轮次状态失败'
        }), 500


@app.route('/api/package_block', methods=['POST'])
def api_package_block():
    """打包区块（由获胜矿工执行）"""
    global mining_round_active, mining_round_data

    try:
        if not mining_round_active:
            return jsonify({'error': '没有进行中的挖矿轮次'}), 400

        if not mining_round_data['block_ready']:
            return jsonify({'error': '区块还未准备好'}), 400

        if mining_round_data['round_complete']:
            return jsonify({'error': '本轮挖矿已完成'}), 400

        winner = mining_round_data['winner']
        if not winner:
            return jsonify({'error': '没有获胜者'}), 400

        # 获取获胜者的钱包
        winner_wallet = wallet_manager.get_wallet(winner['name'])
        if not winner_wallet:
            return jsonify({'error': '获胜者钱包不存在'}), 400

        # 挖矿（包含所有待处理交易）
        try:
            new_block = blockchain.mine_pending_transactions(winner_wallet.address)

            # 计算交易费用 (区块中的交易是字典格式)
            total_fee = 0
            for tx_dict in new_block.transactions:
                if 'fee' in tx_dict:
                    total_fee += tx_dict['fee']

            mining_round_data['round_complete'] = True
            mining_round_active = False

            print(f"🎉 第 {mining_round_data['round_number']} 轮挖矿完成!")
            print(f"🏆 获胜者: {winner['name']}")
            print(f"📦 区块 #{new_block.index} 已打包")
            print(f"💰 获得奖励: {blockchain.mining_reward} BTC + {total_fee} BTC 交易费")

            return jsonify({
                'success': True,
                'message': '区块打包成功',
                'winner': winner['name'],
                'block_index': new_block.index,
                'block_hash': new_block.hash,
                'reward': blockchain.mining_reward,
                'transaction_fee': total_fee,
                'transaction_count': len(new_block.transactions)
            })

        except Exception as e:
            app.logger.error(f"Error mining block: {str(e)}")
            return jsonify({'error': f'挖矿失败: {str(e)}'}), 500

    except Exception as e:
        app.logger.error(f"Error packaging block: {str(e)}")
        return jsonify({'error': '打包区块失败'}), 500


@app.route('/api/wallets')
def api_wallets():
    """获取所有钱包信息"""
    try:
        wallets_data = []
        for wallet_name, wallet in wallet_manager.wallets.items():
            balance = blockchain.get_balance(wallet.address)
            wallets_data.append({
                'name': wallet_name,
                'address': wallet.address,
                'balance': balance
            })

        return jsonify({
            'success': True,
            'wallets': wallets_data
        })
    except Exception as e:
        app.logger.error(f"Error getting wallets: {str(e)}")
        return jsonify({'error': '获取钱包信息失败'}), 500


@app.route('/api/wallet_balance')
def api_wallet_balance():
    """获取单个钱包的余额"""
    try:
        wallet_name = request.args.get('wallet_name')
        if not wallet_name:
            return jsonify({'error': '钱包名称不能为空'}), 400

        wallet = wallet_manager.get_wallet(wallet_name)
        if not wallet:
            return jsonify({'error': '钱包不存在'}), 404

        balance = blockchain.get_balance(wallet.address)
        return jsonify({
            'success': True,
            'balance': balance
        })
    except Exception as e:
        app.logger.error(f"Error getting wallet balance: {str(e)}")
        return jsonify({'error': '获取钱包余额失败'}), 500


@app.route('/api/reset_mining_round', methods=['POST'])
def api_reset_mining_round():
    """重置挖矿轮次状态"""
    global mining_round_active, mining_round_data

    try:
        # 强制重置挖矿轮次状态
        mining_round_active = False
        mining_round_data = {
            'round_number': mining_round_data['round_number'],
            'participants': [],
            'winner': None,
            'start_time': 0,
            'block_ready': False,
            'round_complete': False,
            'computing_time': 10.0
        }

        print("🔄 挖矿轮次状态已重置")

        return jsonify({
            'success': True,
            'message': '挖矿轮次状态已重置',
            'mining_round_active': mining_round_active
        })
    except Exception as e:
        app.logger.error(f"Error resetting mining round: {str(e)}")
        return jsonify({'error': '重置挖矿轮次失败'}), 500


@app.route('/api/blockchain_stats')
def api_blockchain_stats():
    """获取区块链统计信息"""
    try:
        stats = {
            'height': len(blockchain.chain),
            'difficulty': blockchain.difficulty,
            'pending_transactions': len(blockchain.pending_transactions),
            'mining_active': mining_active,
            'mining_round_active': mining_round_active,
            'latest_block': {
                'index': blockchain.get_latest_block().index,
                'timestamp': blockchain.get_latest_block().timestamp,
                'hash': blockchain.get_latest_block().hash,
                'transaction_count': len(blockchain.get_latest_block().transactions)
            } if blockchain.chain else None
        }

        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Error getting blockchain stats: {str(e)}")
        return jsonify({'error': '获取统计信息失败'}), 500


@app.route('/api/config')
def api_config():
    """获取前端配置"""
    try:
        return jsonify(config.get_frontend_config())
    except Exception as e:
        app.logger.error(f"Error getting config: {str(e)}")
        return jsonify({'error': '获取配置失败'}), 500


if __name__ == '__main__':

    port = 5001  # 默认使用5001
    alice = wallet_manager.create_wallet("Alice")
    bob = wallet_manager.create_wallet("Bob")
    charlie = wallet_manager.create_wallet("Charlie")
    app.run(debug=True, host='0.0.0.0', port=port)
