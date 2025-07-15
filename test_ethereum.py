#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
以太坊智能合约演示

演示以太坊智能合约系统的完整功能：
- 智能合约部署
- 函数调用
- 事件监听
- Gas计算
- 账户管理
- 区块链操作
"""

import ethereum
from ethereum import (
    SmartContract, EthereumVM, ContractManager,
    SolidityCompiler, AccountManager, EthereumBlockchain,
    EthereumTransaction
)


def demo_basic_smart_contract():
    """演示基本智能合约功能"""
    print("\n" + "=" * 60)
    print("基本智能合约演示")
    print("=" * 60)

    # 创建虚拟机
    vm = EthereumVM()

    # 创建简单合约
    contract_code = """
    pragma solidity ^0.8.0;

    contract SimpleStorage {
        uint256 public storedData;
        address public owner;

        event DataStored(uint256 data, address indexed by);

        constructor(uint256 initialValue) {
            storedData = initialValue;
            owner = msg.sender;
        }

        function set(uint256 x) public {
            storedData = x;
            emit DataStored(x, msg.sender);
        }

        function get() public view returns (uint256) {
            return storedData;
        }
    }
    """

    # 编译合约
    compiler = SolidityCompiler()
    compile_result = compiler.compile(contract_code)

    print(f"合约编译结果:")
    print(f"  字节码长度: {len(compile_result.bytecode)}")
    print(f"  ABI函数数量: {len(compile_result.abi)}")

    # 创建合约实例
    contract = SmartContract(compile_result.bytecode, compile_result.abi)

    # 部署合约
    deployer = "0x1234567890123456789012345678901234567890"
    contract_address = vm.deploy_contract(contract, [42], deployer)

    print(f"合约地址: {contract_address}")

    # 调用合约函数
    result = vm.call_contract(contract_address, "get_value", ["storedData"])
    print(f"初始值: {result}")

    # 设置新值
    vm.call_contract(contract_address, "set_value", ["storedData", 100])
    result = vm.call_contract(contract_address, "get_value", ["storedData"])
    print(f"新值: {result}")

    # 获取合约事件
    events = vm.get_contract_events(contract_address)
    print(f"事件数量: {len(events)}")
    for event in events:
        print(f"  {event.name}: {event.args}")


def demo_contract_manager():
    """演示合约管理器功能"""
    print("\n" + "=" * 60)
    print("合约管理器演示")
    print("=" * 60)

    # 创建合约管理器
    manager = ContractManager()

    # 注册合约模板
    simple_storage_template = {
        "code": """
        pragma solidity ^0.8.0;
        contract SimpleStorage {
            uint256 public data;
            function set(uint256 x) public { data = x; }
            function get() public view returns (uint256) { return data; }
        }
        """,
        "abi": [
            {
                "type": "function",
                "name": "set",
                "inputs": [{"name": "x", "type": "uint256"}],
                "outputs": []
            },
            {
                "type": "function",
                "name": "get",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint256"}]
            }
        ]
    }

    manager.register_template("SimpleStorage", simple_storage_template)

    # 从模板部署合约
    deployer = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    contract_address = manager.deploy_from_template(
        "SimpleStorage",
        deployer,
        contract_name="我的存储合约",
        version="1.0.0",
        description="简单的数据存储合约",
        tags=["storage", "simple"]
    )

    print(f"合约地址: {contract_address}")

    # 查找合约
    contracts = manager.find_contracts(name="我的存储合约")
    print(f"找到合约: {len(contracts)} 个")

    for contract_info in contracts:
        print(f"  名称: {contract_info.name}")
        print(f"  版本: {contract_info.version}")
        print(f"  描述: {contract_info.description}")
        print(f"  标签: {contract_info.tags}")

    # 批量调用
    calls = [
        {"address": contract_address, "function": "set_value", "args": ["data", 123]},
        {"address": contract_address, "function": "get_value", "args": ["data"]}
    ]

    results = manager.batch_call(calls)
    print(f"批量调用结果:")
    for i, result in enumerate(results):
        print(f"  {i+1}. 成功: {result['success']}, 结果: {result.get('result', result.get('error'))}")


def demo_account_management():
    """演示账户管理功能"""
    print("\n" + "=" * 60)
    print("账户管理演示")
    print("=" * 60)

    # 创建账户管理器
    account_manager = AccountManager()

    # 创建多个账户
    accounts = account_manager.create_multiple_accounts(
        3, initial_balance=1000000000000000000)  # 1 ETH

    print(f"创建了 {len(accounts)} 个账户:")
    for i, account in enumerate(accounts):
        print(f"  {i+1}. {account.address[:10]}... 余额: {account.balance/1e18:.2f} ETH")

    # 转账
    from_account = accounts[0]
    to_account = accounts[1]
    transfer_amount = 100000000000000000  # 0.1 ETH

    print(f"\n转账演示:")
    print(f"  从: {from_account.address[:10]}...")
    print(f"  到: {to_account.address[:10]}...")
    print(f"  金额: {transfer_amount/1e18:.2f} ETH")

    success = account_manager.transfer(from_account.address, to_account.address, transfer_amount)
    print(f"  结果: {'成功' if success else '失败'}")

    # 显示转账后余额
    print(f"\n转账后余额:")
    for i, account in enumerate(accounts):
        balance = account_manager.get_balance(account.address)
        print(f"  {i+1}. {account.address[:10]}... 余额: {balance/1e18:.2f} ETH")

    # 账户统计
    stats = account_manager.get_account_statistics()
    print(f"\n账户统计:")
    print(f"  总账户数: {stats['total_accounts']}")
    print(f"  总余额: {stats['total_balance']/1e18:.2f} ETH")
    print(f"  平均余额: {stats['average_balance']/1e18:.2f} ETH")


def demo_blockchain_operations():
    """演示区块链操作"""
    print("\n" + "=" * 60)
    print("区块链操作演示")
    print("=" * 60)

    # 创建区块链
    blockchain = EthereumBlockchain()

    # 创建交易
    tx1 = EthereumTransaction(
        from_address="0x1111111111111111111111111111111111111111",
        to_address="0x2222222222222222222222222222222222222222",
        value=1000000000000000000,  # 1 ETH
        gas_limit=21000,
        gas_price=20000000000  # 20 Gwei
    )

    tx2 = EthereumTransaction(
        from_address="0x3333333333333333333333333333333333333333",
        to_address="0x4444444444444444444444444444444444444444",
        value=500000000000000000,  # 0.5 ETH
        gas_limit=21000,
        gas_price=25000000000  # 25 Gwei
    )

    # 添加交易到交易池
    blockchain.add_transaction(tx1)
    blockchain.add_transaction(tx2)

    print(f"待处理交易: {blockchain.get_pending_transactions_count()}")

    # 挖矿
    miner_address = "0x5555555555555555555555555555555555555555"
    new_block = blockchain.mine_block(miner_address)

    print(f"挖出新区块:")
    print(f"  区块号: {new_block.block_number}")
    print(f"  区块哈希: {new_block.block_hash[:16]}...")
    print(f"  交易数量: {new_block.get_transaction_count()}")
    print(f"  Gas使用: {new_block.gas_used:,}")

    # 区块链信息
    chain_info = blockchain.get_blockchain_info()
    print(f"\n区块链状态:")
    print(f"  区块数量: {chain_info['total_blocks']}")
    print(f"  总难度: {chain_info['total_difficulty']:,}")
    print(f"  待处理交易: {chain_info['pending_transactions']}")
    print(f"  平均出块时间: {chain_info['average_block_time']:.1f}秒")


def demo_gas_calculation():
    """演示Gas计算"""
    print("\n" + "=" * 60)
    print("Gas计算演示")
    print("=" * 60)

    # 创建虚拟机
    vm = EthereumVM()

    # 创建一个复杂的合约
    complex_contract_code = """
    pragma solidity ^0.8.0;

    contract ComplexContract {
        mapping(address => uint256) public balances;
        uint256 public totalSupply;

        function transfer(address to, uint256 amount) public {
            require(balances[msg.sender] >= amount, "Insufficient balance");
            balances[msg.sender] -= amount;
            balances[to] += amount;
        }

        function mint(address to, uint256 amount) public {
            balances[to] += amount;
            totalSupply += amount;
        }
    }
    """

    # 编译合约
    compiler = SolidityCompiler()
    compile_result = compiler.compile(complex_contract_code)
    contract = SmartContract(compile_result.bytecode, compile_result.abi)

    # 部署合约并计算Gas
    deployer = "0xdeployer123456789012345678901234567890"
    deploy_gas = vm.estimate_gas_for_deployment(contract, [])
    print(f"部署合约估计Gas: {deploy_gas:,}")

    contract_address = vm.deploy_contract(contract, [], deployer)
    print(f"合约部署到: {contract_address}")

    # 调用函数并计算Gas
    mint_gas = vm.estimate_gas_for_call(contract_address, "mint", [deployer, 1000])
    print(f"mint函数估计Gas: {mint_gas:,}")

    transfer_gas = vm.estimate_gas_for_call(
        contract_address, "transfer",
        ["0xrecipient12345678901234567890123456", 100]
    )
    print(f"transfer函数估计Gas: {transfer_gas:,}")

    # Gas价格分析
    gas_prices = [10, 20, 50, 100, 200]  # Gwei
    print(f"\nGas成本分析 (ETH价格假设$2000):")
    for price in gas_prices:
        cost_wei = transfer_gas * price * 10**9
        cost_eth = cost_wei / 10**18
        cost_usd = cost_eth * 2000
        print(f"  {price} Gwei: {cost_eth:.6f} ETH (${cost_usd:.3f})")


def demo_complete_dapp():
    """演示完整DApp"""
    print("\n" + "=" * 60)
    print("完整DApp演示")
    print("=" * 60)

    # 创建系统组件
    vm = EthereumVM()
    blockchain = EthereumBlockchain()
    account_manager = AccountManager()

    # 创建账户
    accounts = account_manager.create_multiple_accounts(3, initial_balance=5 * 10**18)
    alice, bob, charlie = accounts

    print(f"DApp参与者:")
    print(f"  Alice: {alice.address[:10]}...")
    print(f"  Bob: {bob.address[:10]}...")
    print(f"  Charlie: {charlie.address[:10]}...")

    # 部署代币合约
    token_contract_code = """
    pragma solidity ^0.8.0;

    contract SimpleToken {
        string public name = "DemoToken";
        string public symbol = "DEMO";
        uint256 public totalSupply;
        mapping(address => uint256) public balanceOf;

        event Transfer(address indexed from, address indexed to, uint256 value);

        constructor(uint256 _totalSupply) {
            totalSupply = _totalSupply;
            balanceOf[msg.sender] = _totalSupply;
        }

        function transfer(address to, uint256 value) public returns (bool) {
            require(balanceOf[msg.sender] >= value, "Insufficient balance");
            balanceOf[msg.sender] -= value;
            balanceOf[to] += value;
            emit Transfer(msg.sender, to, value);
            return true;
        }
    }
    """

    compiler = SolidityCompiler()
    compile_result = compiler.compile(token_contract_code)
    token_contract = SmartContract(compile_result.bytecode, compile_result.abi)

    # Alice部署代币合约
    token_address = vm.deploy_contract(token_contract, [1000000], alice.address)
    print(f"\n代币合约部署: {token_address}")

    # 检查Alice的代币余额
    alice_token_balance = vm.call_contract(token_address, "get_value", ["balanceOf", alice.address])
    print(f"Alice代币余额: {alice_token_balance}")

    # Alice向Bob转账代币
    vm.call_contract(token_address, "transfer", [bob.address, 100000], sender=alice.address)
    print(f"Alice向Bob转账100,000代币")

    # 检查转账后余额
    alice_balance = vm.call_contract(token_address, "get_value", ["balanceOf", alice.address])
    bob_balance = vm.call_contract(token_address, "get_value", ["balanceOf", bob.address])
    print(f"转账后余额:")
    print(f"  Alice: {alice_balance}代币")
    print(f"  Bob: {bob_balance}代币")

    # 检查事件
    events = vm.get_contract_events(token_address)
    print(f"\n合约事件:")
    for event in events:
        print(f"  {event.name}: {event.args}")


def main():
    """主函数"""
    print("以太坊智能合约系统演示")
    print("=" * 60)

    try:
        # 运行各个演示
        demo_basic_smart_contract()
        demo_contract_manager()
        demo_account_management()
        demo_blockchain_operations()
        demo_gas_calculation()
        demo_complete_dapp()

        print(f"\n演示完成！")
        print(f"功能总结:")
        print(f"  智能合约编译和部署")
        print(f"  合约函数调用")
        print(f"  事件监听")
        print(f"  Gas计算")
        print(f"  账户管理")
        print(f"  区块链操作")
        print(f"  完整DApp演示")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
