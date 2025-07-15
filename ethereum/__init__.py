#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌐 Ethereum智能合约模块

这个模块实现了简化版的以太坊智能合约系统，包括：
- 智能合约定义和部署
- 虚拟机执行环境
- 状态管理
- Gas计算
- 事件系统

作者: AI Assistant
版本: 1.0.0
"""

from .smart_contract import SmartContract, ContractState, ContractEvent
from .virtual_machine import EthereumVM, VMError, Gas
from .contract_manager import ContractManager, ContractRegistry
from .solidity_compiler import SolidityCompiler, CompilerError
from .account import EthereumAccount, AccountManager
from .blockchain import EthereumBlockchain, EthereumBlock, EthereumTransaction

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 导出主要类
__all__ = [
    'SmartContract',
    'ContractState',
    'ContractEvent',
    'EthereumVM',
    'VMError',
    'Gas',
    'ContractManager',
    'ContractRegistry',
    'SolidityCompiler',
    'CompilerError',
    'EthereumAccount',
    'AccountManager',
    'EthereumBlockchain',
    'EthereumBlock',
    'EthereumTransaction'
]


def create_ethereum_vm():
    """创建以太坊虚拟机实例"""
    return EthereumVM()


def create_contract_manager():
    """创建合约管理器实例"""
    return ContractManager()


def create_account_manager():
    """创建账户管理器实例"""
    return AccountManager()


def create_ethereum_blockchain():
    """创建以太坊区块链实例"""
    return EthereumBlockchain()


def deploy_contract(contract_code: str, constructor_args: list = None):
    """部署智能合约的便捷函数"""
    vm = create_ethereum_vm()
    contract = SmartContract(contract_code)
    return vm.deploy_contract(contract, constructor_args or [])


def print_ethereum_info():
    """打印以太坊模块信息"""
    print(f"\n🌐 Ethereum模块 v{__version__} by {__author__}")
    print("\n=== 智能合约功能 ===")
    print("  ✅ 智能合约部署和执行")
    print("  ✅ 以太坊虚拟机(EVM)")
    print("  ✅ Gas计算系统")
    print("  ✅ 状态管理")
    print("  ✅ 事件系统")
    print("  ✅ Solidity编译器")
    print("  ✅ 账户管理")
    print("  ✅ 以太坊区块链")
    print()
