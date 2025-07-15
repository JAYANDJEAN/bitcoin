#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
👤 以太坊账户管理

实现以太坊账户系统：
- 外部账户(EOA)
- 账户余额管理
- 交易签名
- 密钥管理
"""

import hashlib
import secrets
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class EthereumAccount:
    """以太坊账户"""
    address: str
    private_key: str = ""
    public_key: str = ""
    balance: int = 0  # wei
    nonce: int = 0
    creation_time: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "address": self.address,
            "balance": self.balance,
            "nonce": self.nonce,
            "creation_time": self.creation_time
        }

    def __str__(self) -> str:
        return f"Account(address={self.address}, balance={self.balance} wei)"


class AccountManager:
    """账户管理器"""

    def __init__(self):
        self.accounts: Dict[str, EthereumAccount] = {}
        self.address_to_private_key: Dict[str, str] = {}

    def create_account(self, initial_balance: int = 0) -> EthereumAccount:
        """
        创建新账户

        Args:
            initial_balance: 初始余额(wei)

        Returns:
            新创建的账户
        """
        # 生成私钥
        private_key = secrets.token_hex(32)

        # 生成公钥（简化实现）
        public_key = hashlib.sha256(private_key.encode()).hexdigest()

        # 生成地址
        address = "0x" + hashlib.sha256(public_key.encode()).hexdigest()[:40]

        # 创建账户
        account = EthereumAccount(
            address=address,
            private_key=private_key,
            public_key=public_key,
            balance=initial_balance
        )

        # 存储账户
        self.accounts[address] = account
        self.address_to_private_key[address] = private_key

        return account

    def import_account(self, private_key: str, initial_balance: int = 0) -> EthereumAccount:
        """
        导入账户

        Args:
            private_key: 私钥
            initial_balance: 初始余额(wei)

        Returns:
            导入的账户
        """
        # 生成公钥
        public_key = hashlib.sha256(private_key.encode()).hexdigest()

        # 生成地址
        address = "0x" + hashlib.sha256(public_key.encode()).hexdigest()[:40]

        # 创建账户
        account = EthereumAccount(
            address=address,
            private_key=private_key,
            public_key=public_key,
            balance=initial_balance
        )

        # 存储账户
        self.accounts[address] = account
        self.address_to_private_key[address] = private_key

        return account

    def get_account(self, address: str) -> Optional[EthereumAccount]:
        """获取账户"""
        return self.accounts.get(address)

    def get_balance(self, address: str) -> int:
        """获取账户余额"""
        account = self.accounts.get(address)
        return account.balance if account else 0

    def set_balance(self, address: str, balance: int):
        """设置账户余额"""
        if address in self.accounts:
            self.accounts[address].balance = balance
        else:
            # 创建新账户
            account = EthereumAccount(address=address, balance=balance)
            self.accounts[address] = account

    def transfer(self, from_address: str, to_address: str, amount: int) -> bool:
        """
        转账

        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 转账金额(wei)

        Returns:
            转账是否成功
        """
        # 检查发送方账户
        from_account = self.accounts.get(from_address)
        if not from_account:
            raise ValueError(f"发送方账户不存在: {from_address}")

        if from_account.balance < amount:
            raise ValueError("余额不足")

        # 检查接收方账户
        to_account = self.accounts.get(to_address)
        if not to_account:
            # 创建接收方账户
            to_account = EthereumAccount(address=to_address)
            self.accounts[to_address] = to_account

        # 执行转账
        from_account.balance -= amount
        to_account.balance += amount
        from_account.nonce += 1

        return True

    def sign_transaction(self, from_address: str, transaction_data: Dict[str, Any]) -> str:
        """
        签名交易

        Args:
            from_address: 发送方地址
            transaction_data: 交易数据

        Returns:
            交易签名
        """
        private_key = self.address_to_private_key.get(from_address)
        if not private_key:
            raise ValueError(f"未找到私钥: {from_address}")

        # 简化的签名实现
        transaction_str = str(transaction_data)
        signature_data = f"{private_key}{transaction_str}".encode()
        signature = hashlib.sha256(signature_data).hexdigest()

        return signature

    def verify_signature(self, address: str, transaction_data: Dict[str, Any],
                         signature: str) -> bool:
        """
        验证签名

        Args:
            address: 签名者地址
            transaction_data: 交易数据
            signature: 签名

        Returns:
            签名是否有效
        """
        try:
            expected_signature = self.sign_transaction(address, transaction_data)
            return signature == expected_signature
        except BaseException:
            return False

    def list_accounts(self) -> List[EthereumAccount]:
        """列出所有账户"""
        return list(self.accounts.values())

    def get_total_balance(self) -> int:
        """获取所有账户总余额"""
        return sum(account.balance for account in self.accounts.values())

    def get_account_count(self) -> int:
        """获取账户数量"""
        return len(self.accounts)

    def fund_account(self, address: str, amount: int):
        """为账户充值"""
        account = self.accounts.get(address)
        if account:
            account.balance += amount
        else:
            # 创建新账户
            account = EthereumAccount(address=address, balance=amount)
            self.accounts[address] = account

    def create_multiple_accounts(
            self,
            count: int,
            initial_balance: int = 0) -> List[EthereumAccount]:
        """批量创建账户"""
        accounts = []
        for _ in range(count):
            account = self.create_account(initial_balance)
            accounts.append(account)
        return accounts

    def export_accounts(self, include_private_keys: bool = False) -> Dict[str, Any]:
        """导出账户数据"""
        export_data = {
            "timestamp": int(time.time()),
            "account_count": len(self.accounts),
            "total_balance": self.get_total_balance(),
            "accounts": {}
        }

        for address, account in self.accounts.items():
            account_data = account.to_dict()

            if include_private_keys:
                account_data["private_key"] = self.address_to_private_key.get(address, "")

            export_data["accounts"][address] = account_data

        return export_data

    def import_accounts(self, import_data: Dict[str, Any]):
        """导入账户数据"""
        for address, account_data in import_data.get("accounts", {}).items():
            account = EthereumAccount(
                address=address,
                balance=account_data.get("balance", 0),
                nonce=account_data.get("nonce", 0),
                creation_time=account_data.get("creation_time", int(time.time()))
            )

            self.accounts[address] = account

            # 导入私钥（如果存在）
            private_key = account_data.get("private_key")
            if private_key:
                self.address_to_private_key[address] = private_key

    def get_account_statistics(self) -> Dict[str, Any]:
        """获取账户统计信息"""
        balances = [account.balance for account in self.accounts.values()]

        return {
            "total_accounts": len(self.accounts),
            "total_balance": sum(balances),
            "average_balance": sum(balances) / len(balances) if balances else 0,
            "max_balance": max(balances) if balances else 0,
            "min_balance": min(balances) if balances else 0,
            "accounts_with_balance": len([b for b in balances if b > 0]),
            "empty_accounts": len([b for b in balances if b == 0])
        }

    def cleanup_empty_accounts(self) -> int:
        """清理空账户"""
        empty_addresses = [
            addr for addr, account in self.accounts.items()
            if account.balance == 0 and account.nonce == 0
        ]

        for address in empty_addresses:
            del self.accounts[address]
            if address in self.address_to_private_key:
                del self.address_to_private_key[address]

        return len(empty_addresses)

    def __str__(self) -> str:
        return f"AccountManager(accounts={len(self.accounts)}, total_balance={self.get_total_balance()} wei)"
