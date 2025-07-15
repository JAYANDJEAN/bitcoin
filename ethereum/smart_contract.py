#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📝 智能合约核心模块

实现智能合约的基本功能：
- 合约定义和字节码
- 状态存储和管理
- 事件发射和监听
- 函数调用接口
"""

import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ContractState(Enum):
    """合约状态"""
    CREATED = "created"
    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    DESTROYED = "destroyed"


@dataclass
class ContractEvent:
    """合约事件"""
    name: str
    args: Dict[str, Any]
    block_number: int
    transaction_hash: str
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class ContractFunction:
    """合约函数"""
    name: str
    inputs: List[Dict[str, str]]
    outputs: List[Dict[str, str]]
    payable: bool = False
    view: bool = False
    pure: bool = False


class SmartContract:
    """智能合约类"""

    def __init__(self, contract_code: str, abi: List[Dict] = None):
        """
        初始化智能合约

        Args:
            contract_code: 合约代码或字节码
            abi: 应用程序二进制接口
        """
        self.contract_code = contract_code
        self.abi = abi or []
        self.address: Optional[str] = None
        self.state = ContractState.CREATED
        self.storage: Dict[str, Any] = {}
        self.events: List[ContractEvent] = []
        self.functions: Dict[str, ContractFunction] = {}
        self.owner: Optional[str] = None
        self.balance: int = 0  # wei
        self.creation_time = int(time.time())

        # 解析ABI
        self._parse_abi()

        # 生成合约地址
        self._generate_address()

    def _parse_abi(self):
        """解析ABI，提取函数信息"""
        for item in self.abi:
            if item.get('type') == 'function':
                func = ContractFunction(
                    name=item['name'],
                    inputs=item.get('inputs', []),
                    outputs=item.get('outputs', []),
                    payable=item.get('payable', False),
                    view=item.get('stateMutability') == 'view',
                    pure=item.get('stateMutability') == 'pure'
                )
                self.functions[func.name] = func

    def _generate_address(self):
        """生成合约地址"""
        data = f"{self.contract_code}{self.creation_time}".encode()
        hash_obj = hashlib.sha256(data)
        self.address = "0x" + hash_obj.hexdigest()[:40]

    def deploy(self, deployer_address: str, constructor_args: List[Any] = None):
        """
        部署合约

        Args:
            deployer_address: 部署者地址
            constructor_args: 构造函数参数
        """
        if self.state != ContractState.CREATED:
            raise ValueError("合约已经部署")

        self.owner = deployer_address
        self.state = ContractState.DEPLOYED

        # 执行构造函数
        if constructor_args:
            self.storage["constructor_args"] = constructor_args

        # 发射部署事件
        self.emit_event("ContractDeployed", {
            "deployer": deployer_address,
            "address": self.address,
            "timestamp": int(time.time())
        })

    def call_function(self, function_name: str, args: List[Any] = None,
                      caller: str = None, value: int = 0) -> Any:
        """
        调用合约函数

        Args:
            function_name: 函数名
            args: 函数参数
            caller: 调用者地址
            value: 发送的以太币数量(wei)

        Returns:
            函数返回值
        """
        if self.state not in [ContractState.DEPLOYED, ContractState.ACTIVE]:
            raise ValueError("合约未部署或已暂停")

        args = args or []

        # 检查是否是ABI中定义的函数
        if function_name in self.functions:
            func = self.functions[function_name]
            # 检查payable
            if value > 0 and not func.payable:
                raise ValueError("函数不接受以太币")

        # 更新余额
        if value > 0:
            self.balance += value

        # 执行函数
        result = self._execute_function(function_name, args, caller)

        # 发射函数调用事件
        self.emit_event("FunctionCalled", {
            "function": function_name,
            "caller": caller,
            "args": args,
            "value": value
        })

        return result

    def _execute_function(self, function_name: str, args: List[Any], caller: str) -> Any:
        """
        执行具体函数逻辑

        这里实现一些示例函数，实际应用中需要根据合约代码执行
        """
        if function_name == "get_balance":
            return self.balance

        elif function_name == "get_owner":
            return self.owner

        elif function_name == "set_value":
            if len(args) < 2:
                raise ValueError("参数不足")
            key, value = args[0], args[1]
            self.storage[key] = value
            return True

        elif function_name == "get_value":
            if len(args) < 1:
                raise ValueError("参数不足")
            key = args[0]
            return self.storage.get(key)

        elif function_name == "transfer":
            if len(args) < 2:
                raise ValueError("参数不足")
            to_address, amount = args[0], args[1]
            if self.balance < amount:
                raise ValueError("余额不足")
            self.balance -= amount
            # 这里应该实际转账，简化实现只是减少余额
            return True

        elif function_name == "pause":
            if caller != self.owner:
                raise ValueError("只有所有者可以暂停合约")
            self.state = ContractState.PAUSED
            return True

        elif function_name == "unpause":
            if caller != self.owner:
                raise ValueError("只有所有者可以恢复合约")
            self.state = ContractState.ACTIVE
            return True

        elif function_name == "destroy":
            if caller != self.owner:
                raise ValueError("只有所有者可以销毁合约")
            self.state = ContractState.DESTROYED
            return True

        else:
            # 默认函数执行
            return f"执行函数 {function_name} 参数: {args}"

    def emit_event(self, event_name: str, event_args: Dict[str, Any],
                   block_number: int = 0, transaction_hash: str = ""):
        """
        发射事件

        Args:
            event_name: 事件名称
            event_args: 事件参数
            block_number: 区块号
            transaction_hash: 交易哈希
        """
        event = ContractEvent(
            name=event_name,
            args=event_args,
            block_number=block_number,
            transaction_hash=transaction_hash
        )
        self.events.append(event)

    def get_events(self, event_name: str = None, from_block: int = 0) -> List[ContractEvent]:
        """
        获取事件

        Args:
            event_name: 事件名称过滤器
            from_block: 起始区块号

        Returns:
            事件列表
        """
        events = self.events

        if event_name:
            events = [e for e in events if e.name == event_name]

        if from_block > 0:
            events = [e for e in events if e.block_number >= from_block]

        return events

    def get_storage(self, key: str = None) -> Any:
        """
        获取存储数据

        Args:
            key: 存储键，如果为None则返回所有存储

        Returns:
            存储值或所有存储
        """
        if key is None:
            return self.storage.copy()
        return self.storage.get(key)

    def set_storage(self, key: str, value: Any):
        """
        设置存储数据

        Args:
            key: 存储键
            value: 存储值
        """
        self.storage[key] = value

    def get_info(self) -> Dict[str, Any]:
        """获取合约信息"""
        return {
            "address": self.address,
            "state": self.state.value,
            "owner": self.owner,
            "balance": self.balance,
            "creation_time": self.creation_time,
            "functions": list(self.functions.keys()),
            "events_count": len(self.events),
            "storage_size": len(self.storage)
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "address": self.address,
            "contract_code": self.contract_code,
            "abi": self.abi,
            "state": self.state.value,
            "storage": self.storage,
            "owner": self.owner,
            "balance": self.balance,
            "creation_time": self.creation_time,
            "events": [
                {
                    "name": e.name,
                    "args": e.args,
                    "block_number": e.block_number,
                    "transaction_hash": e.transaction_hash,
                    "timestamp": e.timestamp
                }
                for e in self.events
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmartContract':
        """从字典创建合约实例"""
        contract = cls(data["contract_code"], data.get("abi", []))
        contract.address = data["address"]
        contract.state = ContractState(data["state"])
        contract.storage = data.get("storage", {})
        contract.owner = data.get("owner")
        contract.balance = data.get("balance", 0)
        contract.creation_time = data.get("creation_time", int(time.time()))

        # 恢复事件
        for event_data in data.get("events", []):
            event = ContractEvent(
                name=event_data["name"],
                args=event_data["args"],
                block_number=event_data["block_number"],
                transaction_hash=event_data["transaction_hash"],
                timestamp=event_data["timestamp"]
            )
            contract.events.append(event)

        return contract

    def __str__(self) -> str:
        return f"SmartContract(address={self.address}, state={self.state.value})"


# 预定义的合约模板
class ContractTemplates:
    """合约模板"""

    @staticmethod
    def erc20_token() -> Dict[str, Any]:
        """ERC20代币合约模板"""
        return {
            "code": """
            pragma solidity ^0.8.0;

            contract ERC20Token {
                string public name;
                string public symbol;
                uint8 public decimals;
                uint256 public totalSupply;

                mapping(address => uint256) public balanceOf;
                mapping(address => mapping(address => uint256)) public allowance;

                event Transfer(address indexed from, address indexed to, uint256 value);
                event Approval(address indexed owner, address indexed spender, uint256 value);

                constructor(string memory _name, string memory _symbol, uint8 _decimals, uint256 _totalSupply) {
                    name = _name;
                    symbol = _symbol;
                    decimals = _decimals;
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

                function approve(address spender, uint256 value) public returns (bool) {
                    allowance[msg.sender][spender] = value;
                    emit Approval(msg.sender, spender, value);
                    return true;
                }

                function transferFrom(address from, address to, uint256 value) public returns (bool) {
                    require(balanceOf[from] >= value, "Insufficient balance");
                    require(allowance[from][msg.sender] >= value, "Insufficient allowance");
                    balanceOf[from] -= value;
                    balanceOf[to] += value;
                    allowance[from][msg.sender] -= value;
                    emit Transfer(from, to, value);
                    return true;
                }
            }
            """,
            "abi": [
                {
                    "type": "constructor",
                    "inputs": [
                        {"name": "_name", "type": "string"},
                        {"name": "_symbol", "type": "string"},
                        {"name": "_decimals", "type": "uint8"},
                        {"name": "_totalSupply", "type": "uint256"}
                    ]
                },
                {
                    "type": "function",
                    "name": "transfer",
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "value", "type": "uint256"}
                    ],
                    "outputs": [{"name": "", "type": "bool"}],
                    "stateMutability": "nonpayable"
                },
                {
                    "type": "function",
                    "name": "balanceOf",
                    "inputs": [{"name": "account", "type": "address"}],
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view"
                }
            ]
        }

    @staticmethod
    def simple_storage() -> Dict[str, Any]:
        """简单存储合约模板"""
        return {
            "code": """
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

                function increment() public {
                    storedData += 1;
                    emit DataStored(storedData, msg.sender);
                }
            }
            """,
            "abi": [
                {
                    "type": "constructor",
                    "inputs": [{"name": "initialValue", "type": "uint256"}]
                },
                {
                    "type": "function",
                    "name": "set",
                    "inputs": [{"name": "x", "type": "uint256"}],
                    "outputs": [],
                    "stateMutability": "nonpayable"
                },
                {
                    "type": "function",
                    "name": "get",
                    "inputs": [],
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view"
                },
                {
                    "type": "function",
                    "name": "increment",
                    "inputs": [],
                    "outputs": [],
                    "stateMutability": "nonpayable"
                }
            ]
        }

    @staticmethod
    def multi_sig_wallet() -> Dict[str, Any]:
        """多重签名钱包合约模板"""
        return {
            "code": """
            pragma solidity ^0.8.0;

            contract MultiSigWallet {
                address[] public owners;
                uint256 public required;

                struct Transaction {
                    address to;
                    uint256 value;
                    bytes data;
                    bool executed;
                }

                Transaction[] public transactions;
                mapping(uint256 => mapping(address => bool)) public confirmations;

                event Deposit(address indexed sender, uint256 value);
                event Submission(uint256 indexed transactionId);
                event Confirmation(address indexed sender, uint256 indexed transactionId);
                event Execution(uint256 indexed transactionId);

                constructor(address[] memory _owners, uint256 _required) {
                    require(_owners.length > 0 && _required > 0 && _required <= _owners.length);
                    owners = _owners;
                    required = _required;
                }

                function submitTransaction(address to, uint256 value, bytes memory data) public returns (uint256) {
                    uint256 transactionId = transactions.length;
                    transactions.push(Transaction({
                        to: to,
                        value: value,
                        data: data,
                        executed: false
                    }));
                    emit Submission(transactionId);
                    return transactionId;
                }

                function confirmTransaction(uint256 transactionId) public {
                    require(isOwner(msg.sender));
                    require(!confirmations[transactionId][msg.sender]);
                    confirmations[transactionId][msg.sender] = true;
                    emit Confirmation(msg.sender, transactionId);

                    if (isConfirmed(transactionId)) {
                        executeTransaction(transactionId);
                    }
                }

                function executeTransaction(uint256 transactionId) public {
                    require(isConfirmed(transactionId));
                    Transaction storage txn = transactions[transactionId];
                    require(!txn.executed);
                    txn.executed = true;
                    emit Execution(transactionId);
                }

                function isOwner(address addr) public view returns (bool) {
                    for (uint256 i = 0; i < owners.length; i++) {
                        if (owners[i] == addr) {
                            return true;
                        }
                    }
                    return false;
                }

                function isConfirmed(uint256 transactionId) public view returns (bool) {
                    uint256 count = 0;
                    for (uint256 i = 0; i < owners.length; i++) {
                        if (confirmations[transactionId][owners[i]]) {
                            count++;
                        }
                    }
                    return count >= required;
                }

                receive() external payable {
                    emit Deposit(msg.sender, msg.value);
                }
            }
            """,
            "abi": [
                {
                    "type": "constructor",
                    "inputs": [
                        {"name": "_owners", "type": "address[]"},
                        {"name": "_required", "type": "uint256"}
                    ]
                },
                {
                    "type": "function",
                    "name": "submitTransaction",
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "value", "type": "uint256"},
                        {"name": "data", "type": "bytes"}
                    ],
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable"
                }
            ]
        }
