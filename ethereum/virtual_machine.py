#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⚡ 以太坊虚拟机(EVM)

实现简化版的以太坊虚拟机：
- 合约部署和执行
- Gas计算和限制
- 状态管理
- 错误处理
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .smart_contract import SmartContract, ContractState


class VMError(Exception):
    """虚拟机错误"""
    pass


class Gas:
    """Gas计算类"""

    # Gas价格常量
    BASE_GAS = 21000
    CONTRACT_CREATION_GAS = 32000
    STORAGE_SET_GAS = 20000
    STORAGE_CLEAR_GAS = 5000
    STORAGE_READ_GAS = 200
    MEMORY_GAS = 3
    COMPUTATION_GAS = 5

    @classmethod
    def calculate_deployment_gas(cls, code_size: int) -> int:
        """计算部署合约的Gas费用"""
        return cls.CONTRACT_CREATION_GAS + (code_size * 200)

    @classmethod
    def calculate_function_call_gas(cls, function_name: str, args_count: int) -> int:
        """计算函数调用的Gas费用"""
        base_gas = cls.BASE_GAS
        computation_gas = cls.COMPUTATION_GAS * (args_count + 1)
        return base_gas + computation_gas

    @classmethod
    def calculate_storage_gas(cls, operation: str) -> int:
        """计算存储操作的Gas费用"""
        if operation == "set":
            return cls.STORAGE_SET_GAS
        elif operation == "clear":
            return cls.STORAGE_CLEAR_GAS
        elif operation == "read":
            return cls.STORAGE_READ_GAS
        return 0


@dataclass
class ExecutionContext:
    """执行上下文"""
    caller: str
    origin: str
    gas_limit: int
    gas_used: int = 0
    value: int = 0
    block_number: int = 0
    timestamp: int = 0

    def consume_gas(self, amount: int):
        """消耗Gas"""
        if self.gas_used + amount > self.gas_limit:
            raise VMError(f"Gas不足: 需要 {amount}, 剩余 {self.gas_limit - self.gas_used}")
        self.gas_used += amount

    def remaining_gas(self) -> int:
        """剩余Gas"""
        return self.gas_limit - self.gas_used


class EthereumVM:
    """以太坊虚拟机"""

    def __init__(self):
        self.contracts: Dict[str, SmartContract] = {}
        self.accounts: Dict[str, int] = {}  # 地址 -> 余额(wei)
        self.block_number = 0
        self.gas_price = 20000000000  # 20 Gwei

    def deploy_contract(self, contract: SmartContract, constructor_args: List[Any] = None,
                        deployer: str = "0x0", gas_limit: int = 3000000) -> str:
        """
        部署智能合约

        Args:
            contract: 智能合约实例
            constructor_args: 构造函数参数
            deployer: 部署者地址
            gas_limit: Gas限制

        Returns:
            合约地址
        """
        # 创建执行上下文
        context = ExecutionContext(
            caller=deployer,
            origin=deployer,
            gas_limit=gas_limit,
            block_number=self.block_number,
            timestamp=int(time.time())
        )

        try:
            # 计算部署Gas费用
            deployment_gas = Gas.calculate_deployment_gas(len(contract.contract_code))
            context.consume_gas(deployment_gas)

            # 部署合约
            contract.deploy(deployer, constructor_args)

            # 存储合约
            self.contracts[contract.address] = contract

            print(f"✅ 合约部署成功: {contract.address}")
            print(f"⛽ Gas使用: {context.gas_used}/{context.gas_limit}")

            return contract.address

        except Exception as e:
            raise VMError(f"合约部署失败: {e}")

    def call_contract(self, contract_address: str, function_name: str,
                      args: List[Any] = None, caller: str = "0x0",
                      value: int = 0, gas_limit: int = 100000) -> Any:
        """
        调用合约函数

        Args:
            contract_address: 合约地址
            function_name: 函数名
            args: 函数参数
            caller: 调用者地址
            value: 发送的以太币数量(wei)
            gas_limit: Gas限制

        Returns:
            函数返回值
        """
        if contract_address not in self.contracts:
            raise VMError(f"合约不存在: {contract_address}")

        contract = self.contracts[contract_address]
        args = args or []

        # 创建执行上下文
        context = ExecutionContext(
            caller=caller,
            origin=caller,
            gas_limit=gas_limit,
            value=value,
            block_number=self.block_number,
            timestamp=int(time.time())
        )

        try:
            # 计算函数调用Gas费用
            call_gas = Gas.calculate_function_call_gas(function_name, len(args))
            context.consume_gas(call_gas)

            # 检查余额（如果发送以太币）
            if value > 0:
                caller_balance = self.accounts.get(caller, 0)
                if caller_balance < value:
                    raise VMError("余额不足")
                self.accounts[caller] = caller_balance - value

            # 调用合约函数
            result = contract.call_function(function_name, args, caller, value)

            # 如果是存储操作，计算额外Gas
            if function_name in ["set_value", "set"]:
                storage_gas = Gas.calculate_storage_gas("set")
                context.consume_gas(storage_gas)
            elif function_name in ["get_value", "get"]:
                storage_gas = Gas.calculate_storage_gas("read")
                context.consume_gas(storage_gas)

            print(f"✅ 函数调用成功: {function_name}")
            print(f"⛽ Gas使用: {context.gas_used}/{context.gas_limit}")

            return result

        except Exception as e:
            raise VMError(f"函数调用失败: {e}")

    def get_contract(self, address: str) -> Optional[SmartContract]:
        """获取合约实例"""
        return self.contracts.get(address)

    def get_contract_info(self, address: str) -> Dict[str, Any]:
        """获取合约信息"""
        if address not in self.contracts:
            raise VMError(f"合约不存在: {address}")

        contract = self.contracts[address]
        return contract.get_info()

    def get_contract_events(self, address: str, event_name: str = None) -> List:
        """获取合约事件"""
        if address not in self.contracts:
            raise VMError(f"合约不存在: {address}")

        contract = self.contracts[address]
        return contract.get_events(event_name)

    def set_account_balance(self, address: str, balance: int):
        """设置账户余额"""
        self.accounts[address] = balance

    def get_account_balance(self, address: str) -> int:
        """获取账户余额"""
        return self.accounts.get(address, 0)

    def transfer(self, from_address: str, to_address: str, amount: int) -> bool:
        """转账"""
        from_balance = self.accounts.get(from_address, 0)
        if from_balance < amount:
            raise VMError("余额不足")

        self.accounts[from_address] = from_balance - amount
        self.accounts[to_address] = self.accounts.get(to_address, 0) + amount

        return True

    def next_block(self):
        """下一个区块"""
        self.block_number += 1

    def get_vm_state(self) -> Dict[str, Any]:
        """获取虚拟机状态"""
        return {
            "block_number": self.block_number,
            "gas_price": self.gas_price,
            "contracts_count": len(self.contracts),
            "accounts_count": len(self.accounts),
            "total_balance": sum(self.accounts.values()),
            "contracts": {
                addr: contract.get_info()
                for addr, contract in self.contracts.items()
            }
        }

    def estimate_gas(self, operation: str, **kwargs) -> int:
        """估算Gas费用"""
        if operation == "deploy":
            code_size = kwargs.get("code_size", 1000)
            return Gas.calculate_deployment_gas(code_size)
        elif operation == "call":
            function_name = kwargs.get("function_name", "")
            args_count = kwargs.get("args_count", 0)
            return Gas.calculate_function_call_gas(function_name, args_count)
        elif operation == "transfer":
            return Gas.BASE_GAS
        else:
            return Gas.COMPUTATION_GAS

    def simulate_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟交易执行"""
        # 创建VM副本进行模拟
        original_contracts = self.contracts.copy()
        original_accounts = self.accounts.copy()

        try:
            if transaction_data.get("type") == "deploy":
                # 模拟部署
                contract_code = transaction_data.get("code", "")
                contract = SmartContract(contract_code)
                address = self.deploy_contract(
                    contract,
                    transaction_data.get("constructor_args"),
                    transaction_data.get("from"),
                    transaction_data.get("gas_limit", 3000000)
                )
                return {
                    "success": True,
                    "contract_address": address,
                    "gas_used": Gas.calculate_deployment_gas(len(contract_code))
                }

            elif transaction_data.get("type") == "call":
                # 模拟函数调用
                result = self.call_contract(
                    transaction_data.get("to"),
                    transaction_data.get("function"),
                    transaction_data.get("args"),
                    transaction_data.get("from"),
                    transaction_data.get("value", 0),
                    transaction_data.get("gas_limit", 100000)
                )
                return {
                    "success": True,
                    "result": result,
                    "gas_used": Gas.calculate_function_call_gas(
                        transaction_data.get("function", ""),
                        len(transaction_data.get("args", []))
                    )
                }

            else:
                return {"success": False, "error": "未知交易类型"}

        except Exception as e:
            # 恢复状态
            self.contracts = original_contracts
            self.accounts = original_accounts
            return {"success": False, "error": str(e)}

    def __str__(self) -> str:
        return f"EthereumVM(contracts={len(self.contracts)}, block={self.block_number})"
