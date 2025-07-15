#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💳 交易模块
包含交易相关的所有类和功能：UTXO、交易输入输出、交易本身和UTXO集合管理
"""

import json
import time
from typing import List, Dict, Any, Optional

from .config import DEFAULT_TRANSACTION_FEE
from .utils import HashUtils


class UTXO:
    """未花费交易输出 (Unspent Transaction Output)"""

    def __init__(
        self,
        transaction_id: str,
        output_index: int,
        amount: float,
        recipient_address: str
    ):
        """
        初始化UTXO
        Args:
            transaction_id: 交易ID
            output_index: 输出索引
            amount: 金额
            recipient_address: 接收地址
        """
        self.transaction_id = transaction_id
        self.output_index = output_index
        self.amount = amount
        self.recipient_address = recipient_address
        self.is_spent = False  # 是否已花费

    def get_utxo_id(self) -> str:
        """获取UTXO的唯一标识符"""
        return f"{self.transaction_id}:{self.output_index}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "transaction_id": self.transaction_id,
            "output_index": self.output_index,
            "amount": self.amount,
            "recipient_address": self.recipient_address,
            "is_spent": self.is_spent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UTXO':
        """从字典创建UTXO"""
        utxo = cls(
            transaction_id=data['transaction_id'],
            output_index=data['output_index'],
            amount=data['amount'],
            recipient_address=data['recipient_address']
        )
        utxo.is_spent = data.get('is_spent', False)
        return utxo


class TransactionInput:
    """交易输入"""

    def __init__(
        self,
        transaction_id: str,
        output_index: int,
        signature: str = "",
        public_key: str = ""
    ):
        """
        初始化交易输入
        Args:
            transaction_id: 引用的交易ID
            output_index: 引用的输出索引
            signature: 数字签名
            public_key: 公钥
        """
        self.transaction_id = transaction_id
        self.output_index = output_index
        self.signature = signature
        self.public_key = public_key

    def get_utxo_id(self) -> str:
        """获取引用的UTXO ID"""
        return f"{self.transaction_id}:{self.output_index}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "transaction_id": self.transaction_id,
            "output_index": self.output_index,
            "signature": self.signature,
            "public_key": self.public_key
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionInput':
        """从字典创建交易输入"""
        return cls(
            transaction_id=data['transaction_id'],
            output_index=data['output_index'],
            signature=data.get('signature', ''),
            public_key=data.get('public_key', '')
        )


class TransactionOutput:
    """交易输出"""

    def __init__(self, amount: float, recipient_address: str):
        """
        初始化交易输出
        Args:
            amount: 金额
            recipient_address: 接收地址
        """
        self.amount = amount
        self.recipient_address = recipient_address

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "amount": self.amount,
            "recipient_address": self.recipient_address
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionOutput':
        """从字典创建交易输出"""
        return cls(
            amount=data['amount'],
            recipient_address=data['recipient_address']
        )


class AddressValidator:
    """地址验证工具类 - 避免重复创建钱包实例"""

    @staticmethod
    def derive_address_from_public_key(public_key_hex: str) -> str:
        """
        从公钥派生地址（不创建钱包实例）
        Args:
            public_key_hex: 公钥16进制字符串
        Returns:
            str: 派生的地址
        """
        try:
            import base58
            import hashlib
            from .config import BITCOIN_ADDRESS_VERSION

            public_key_bytes = bytes.fromhex(public_key_hex)

            # 1. 对公钥进行SHA256哈希
            sha256_hash = hashlib.sha256(public_key_bytes).digest()
            # 2. 对SHA256结果进行RIPEMD160哈希
            ripemd160 = hashlib.new('ripemd160')
            ripemd160.update(sha256_hash)
            hash160 = ripemd160.digest()
            # 3. 添加版本字节
            versioned_payload = BITCOIN_ADDRESS_VERSION + hash160
            # 4. 计算校验和
            checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
            # 5. 组合并Base58编码
            binary_address = versioned_payload + checksum
            return base58.b58encode(binary_address).decode('utf-8')
        except Exception:
            return ""

    @staticmethod
    def verify_signature_static(message: str, signature_hex: str, public_key_hex: str) -> bool:
        """
        静态方法验证数字签名（避免创建钱包实例）
        Args:
            message: 原始消息
            signature_hex: 签名16进制字符串
            public_key_hex: 公钥16进制字符串
        Returns:
            bool: 签名是否有效
        """
        try:
            from ecdsa import VerifyingKey, SECP256k1
            from ecdsa.util import sigdecode_string

            message_bytes = message.encode('utf-8')
            signature_bytes = bytes.fromhex(signature_hex)
            public_key_bytes = bytes.fromhex(public_key_hex)

            verifying_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
            return verifying_key.verify(signature_bytes, message_bytes, sigdecode=sigdecode_string)
        except Exception:
            return False


class Transaction:
    """交易类 - 支持UTXO模型"""

    def __init__(self, inputs: List[TransactionInput] = None,
                 outputs: List[TransactionOutput] = None,
                 block_height: Optional[int] = None):
        """
        初始化交易
        Args:
            inputs: 交易输入列表
            outputs: 交易输出列表
            block_height: 区块高度（可选，主要用于coinbase交易确保唯一性）
        """
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.timestamp = str(int(time.time()))
        self.block_height = block_height
        self.transaction_id = self._calculate_hash()

    def is_coinbase(self) -> bool:
        """
        判断是否为coinbase交易（挖矿奖励交易）
        Returns:
            bool: 是否为coinbase交易
        """
        # Coinbase交易没有输入，或者输入的transaction_id为空
        if not self.inputs:
            return True
        return all(not input_tx.transaction_id for input_tx in self.inputs)

    def calculate_fee(self, utxo_set) -> float:
        """
        计算交易手续费
        Args:
            utxo_set: UTXO集合
        Returns:
            float: 手续费
        """
        if self.is_coinbase():
            return 0.0

        total_input = self.get_total_input_value(utxo_set)
        total_output = self.get_total_output_value()
        return max(0.0, total_input - total_output)

    def get_total_input_value(self, utxo_set) -> float:
        """
        获取输入总金额
        Args:
            utxo_set: UTXO集合
        Returns:
            float: 输入总金额
        """
        if self.is_coinbase():
            return 0.0

        total = 0.0
        for input_tx in self.inputs:
            utxo_id = input_tx.get_utxo_id()
            if utxo_id in utxo_set:
                utxo = utxo_set[utxo_id]
                total += utxo.amount
        return total

    def get_total_output_value(self) -> float:
        """
        获取输出总金额
        Returns:
            float: 输出总金额
        """
        return sum(output.amount for output in self.outputs)

    def get_input_addresses(self, utxo_set) -> List[str]:
        """
        获取输入地址列表
        Args:
            utxo_set: UTXO集合
        Returns:
            List[str]: 地址列表
        """
        addresses = []
        for input_tx in self.inputs:
            utxo_id = input_tx.get_utxo_id()
            if utxo_id in utxo_set:
                utxo = utxo_set[utxo_id]
                addresses.append(utxo.recipient_address)
        return addresses

    def get_output_addresses(self) -> List[str]:
        """
        获取输出地址列表
        Returns:
            List[str]: 地址列表
        """
        return [output.recipient_address for output in self.outputs]

    def _calculate_hash(self) -> str:
        """计算交易哈希"""
        transaction_data = self.get_transaction_data_for_signature()
        return HashUtils.calculate_transaction_hash(transaction_data)

    def get_transaction_data_for_signature(self) -> str:
        """获取用于签名的交易数据"""
        data = {"inputs": [{"transaction_id": inp.transaction_id,
                            "output_index": inp.output_index} for inp in self.inputs],
                "outputs": [out.to_dict() for out in self.outputs],
                "timestamp": self.timestamp}

        # 为coinbase交易添加区块高度信息以确保唯一性
        if self.is_coinbase() and self.block_height is not None:
            data["block_height"] = self.block_height

        return json.dumps(data, sort_keys=True)

    def sign_transaction(self, wallet, utxo_set=None) -> None:
        """
        对交易进行签名（改进版本 - 为每个输入单独签名）
        Args:
            wallet: 钱包对象
            utxo_set: UTXO集合（可选）
        """
        if self.is_coinbase():
            return  # Coinbase交易不需要签名

        # 为每个输入单独签名（更符合比特币的实际做法）
        for i, input_tx in enumerate(self.inputs):
            # 创建该输入的签名数据
            input_data = self._get_input_signature_data(i)
            signature = wallet.sign_message(input_data)

            # 设置签名和公钥
            input_tx.signature = signature
            input_tx.public_key = wallet.public_key_hex

    def _get_input_signature_data(self, input_index: int) -> str:
        """
        获取特定输入的签名数据
        Args:
            input_index: 输入索引
        Returns:
            str: 签名数据
        """
        # 简化版本：包含交易基本数据和输入索引
        base_data = self.get_transaction_data_for_signature()
        return f"{base_data}:input_{input_index}"

    def verify_signature(self, utxo_set=None) -> bool:
        """
        验证交易签名
        Args:
            utxo_set: UTXO集合（可选）
        Returns:
            bool: 签名是否有效
        """
        if self.is_coinbase():
            return True  # Coinbase交易无需验证签名

        for i, input_tx in enumerate(self.inputs):
            if not input_tx.signature or not input_tx.public_key:
                return False

            # 验证公钥对应的地址是否正确
            if utxo_set and not self._verify_input_address(input_tx, utxo_set):
                return False

            # 验证签名
            input_data = self._get_input_signature_data(i)
            if not AddressValidator.verify_signature_static(
                    input_data, input_tx.signature, input_tx.public_key):
                return False

        return True

    def _verify_input_address(self, input_tx: TransactionInput, utxo_set) -> bool:
        """
        验证输入的地址是否匹配公钥
        Args:
            input_tx: 交易输入
            utxo_set: UTXO集合
        Returns:
            bool: 是否匹配
        """
        utxo_id = input_tx.get_utxo_id()
        if utxo_id not in utxo_set:
            return False

        utxo = utxo_set[utxo_id]
        expected_address = utxo.recipient_address

        # 使用优化的地址验证方法
        derived_address = AddressValidator.derive_address_from_public_key(input_tx.public_key)
        return derived_address == expected_address

    def is_valid(self, utxo_set=None) -> bool:
        """
        验证交易是否有效
        Args:
            utxo_set: UTXO集合（可选）
        Returns:
            bool: 交易是否有效
        """
        # 基本验证
        if not self.outputs:
            return False

        # 检查输出金额是否为正数
        for output in self.outputs:
            if output.amount <= 0:
                return False

        # Coinbase交易特殊处理
        if self.is_coinbase():
            return len(self.outputs) > 0

        # 非Coinbase交易需要有输入
        if not self.inputs:
            return False

        # 验证签名
        if not self.verify_signature(utxo_set):
            return False

        # 验证UTXO约束
        if utxo_set and not self._validate_utxo_constraints(utxo_set):
            return False

        return True

    def _validate_utxo_constraints(self, utxo_set) -> bool:
        """
        验证UTXO约束
        Args:
            utxo_set: UTXO集合
        Returns:
            bool: 约束是否满足
        """
        total_input = 0.0

        for input_tx in self.inputs:
            utxo_id = input_tx.get_utxo_id()

            # 检查UTXO是否存在
            if utxo_id not in utxo_set:
                return False

            utxo = utxo_set[utxo_id]

            # 检查UTXO是否已被花费
            if utxo.is_spent:
                return False

            total_input += utxo.amount

        total_output = self.get_total_output_value()

        # 输入必须大于或等于输出（手续费可以为零）
        return total_input >= total_output

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            "transaction_id": self.transaction_id,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "timestamp": self.timestamp
        }

        # 包含区块高度信息（如果有的话）
        if self.block_height is not None:
            data["block_height"] = self.block_height

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """从字典创建交易"""
        inputs = [TransactionInput.from_dict(inp_data) for inp_data in data['inputs']]
        outputs = [TransactionOutput.from_dict(out_data) for out_data in data['outputs']]

        # 如果数据中包含block_height，在创建时就传入
        block_height = data.get('block_height')
        transaction = cls(inputs=inputs, outputs=outputs, block_height=block_height)

        # 恢复其他属性
        transaction.timestamp = data['timestamp']
        transaction.transaction_id = data['transaction_id']

        return transaction

    @classmethod
    def create_coinbase_transaction(
            cls,
            miner_address: str,
            reward: float,
            block_height: Optional[int] = None) -> 'Transaction':
        """
        创建coinbase交易（挖矿奖励）
        Args:
            miner_address: 矿工地址
            reward: 奖励金额
            block_height: 区块高度（可选，用于确保coinbase交易的唯一性）
        Returns:
            Transaction: coinbase交易
        """
        output = TransactionOutput(reward, miner_address)
        transaction = cls(inputs=[], outputs=[output], block_height=block_height)
        return transaction

    def __str__(self) -> str:
        """交易的字符串表示"""
        input_count = len(self.inputs)
        output_count = len(self.outputs)
        total_output = self.get_total_output_value()

        if self.is_coinbase():
            return f"Coinbase交易 - 奖励: {total_output} BTC"
        else:
            return f"交易 {self.transaction_id[:8]}... - {input_count}输入→{output_count}输出: {total_output} BTC"


class UTXOSet:
    """UTXO集合管理类"""

    def __init__(self):
        """初始化UTXO集合"""
        self.utxos: Dict[str, UTXO] = {}

    def add_utxo(self, utxo: UTXO) -> None:
        """添加UTXO"""
        utxo_id = utxo.get_utxo_id()
        self.utxos[utxo_id] = utxo

    def remove_utxo(self, utxo_id: str) -> None:
        """移除UTXO"""
        if utxo_id in self.utxos:
            del self.utxos[utxo_id]

    def get_utxo(self, utxo_id: str) -> Optional[UTXO]:
        """获取UTXO"""
        return self.utxos.get(utxo_id)

    def get_utxos_by_address(self, address: str) -> List[UTXO]:
        """获取指定地址的所有UTXO"""
        return [utxo for utxo in self.utxos.values()
                if utxo.recipient_address == address and not utxo.is_spent]

    def get_balance(self, address: str) -> float:
        """获取指定地址的余额"""
        return sum(utxo.amount for utxo in self.get_utxos_by_address(address))

    def select_utxos(self, address: str, amount: float) -> List[UTXO]:
        """
        为指定金额选择UTXO
        Args:
            address: 地址
            amount: 需要的金额
        Returns:
            List[UTXO]: 选中的UTXO列表
        """
        available_utxos = self.get_utxos_by_address(address)
        available_utxos.sort(key=lambda x: x.amount, reverse=True)  # 优先选择大额UTXO

        selected_utxos = []
        total_selected = 0.0

        for utxo in available_utxos:
            if total_selected >= amount:
                break
            selected_utxos.append(utxo)
            total_selected += utxo.amount

        return selected_utxos if total_selected >= amount else []

    def update_from_transaction(self, transaction: Transaction) -> None:
        """
        根据交易更新UTXO集合
        Args:
            transaction: 交易对象
        """
        # 移除被消费的UTXO
        for input_tx in transaction.inputs:
            utxo_id = input_tx.get_utxo_id()
            if utxo_id in self.utxos:
                self.utxos[utxo_id].is_spent = True
                # 可以选择立即删除或标记为已花费
                del self.utxos[utxo_id]

        # 添加新的UTXO
        for index, output in enumerate(transaction.outputs):
            utxo = UTXO(
                transaction_id=transaction.transaction_id,
                output_index=index,
                amount=output.amount,
                recipient_address=output.recipient_address
            )
            self.add_utxo(utxo)

    def __contains__(self, utxo_id: str) -> bool:
        """检查UTXO是否存在"""
        return utxo_id in self.utxos

    def __getitem__(self, utxo_id: str) -> UTXO:
        """获取UTXO"""
        return self.utxos[utxo_id]
