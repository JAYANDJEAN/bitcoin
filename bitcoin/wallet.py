#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💼 钱包模块
包含钱包管理相关的类和功能
"""

import secrets
import hashlib
from typing import Dict, List, Optional
import base58
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigdecode_string, sigencode_string

from .config import BITCOIN_ADDRESS_VERSION, PRIVATE_KEY_VERSION


class Wallet:
    """加密货币钱包类"""

    def __init__(self, private_key: Optional[str] = None):
        """
        初始化钱包
        Args:
            private_key: 可选的私钥（16进制字符串），如果不提供则生成新的
        """
        if private_key:
            # 从现有私钥创建钱包
            self.private_key_hex = private_key
            self.private_key_bytes = bytes.fromhex(private_key)
        else:
            # 生成新的私钥
            self.private_key_bytes = secrets.randbits(256).to_bytes(32, byteorder='big')
            self.private_key_hex = self.private_key_bytes.hex()

        # 生成签名密钥对
        self.signing_key = SigningKey.from_string(self.private_key_bytes, curve=SECP256k1)
        self.verifying_key = self.signing_key.get_verifying_key()

        # 生成公钥
        self.public_key_bytes = self.verifying_key.to_string()
        self.public_key_hex = self.public_key_bytes.hex()

        # 生成钱包地址
        self.address = self._generate_address()

    def _generate_address(self) -> str:
        """
        从公钥生成钱包地址（类似比特币地址生成过程）
        """
        # 1. 对公钥进行SHA256哈希
        sha256_hash = hashlib.sha256(self.public_key_bytes).digest()
        # 2. 对SHA256结果进行RIPEMD160哈希
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        hash160 = ripemd160.digest()
        # 3. 添加版本字节（0x00用于主网）
        versioned_payload = BITCOIN_ADDRESS_VERSION + hash160
        # 4. 计算校验和（双SHA256的前4字节）
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
        # 5. 组合版本+哈希+校验和
        binary_address = versioned_payload + checksum
        # 6. Base58编码
        address = base58.b58encode(binary_address).decode('utf-8')
        return address

    def sign_message(self, message: str) -> str:
        """
        使用私钥对消息进行数字签名
        Args:
            message: 要签名的消息
        Returns:
            str: 签名的16进制字符串
        """
        message_bytes = message.encode('utf-8')
        signature = self.signing_key.sign(message_bytes, sigencode=sigencode_string)
        return signature.hex()

    def verify_signature(self, message: str, signature_hex: str, public_key_hex: str) -> bool:
        """
        验证数字签名
        Args:
            message: 原始消息
            signature_hex: 签名的16进制字符串
            public_key_hex: 公钥的16进制字符串
        Returns:
            bool: 签名是否有效
        """
        try:
            message_bytes = message.encode('utf-8')
            signature_bytes = bytes.fromhex(signature_hex)
            public_key_bytes = bytes.fromhex(public_key_hex)
            # 从公钥创建验证密钥
            verifying_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
            # 验证签名
            return verifying_key.verify(signature_bytes, message_bytes, sigdecode=sigdecode_string)
        except Exception:
            return False

    def get_wallet_info(self) -> Dict[str, str]:
        """获取钱包信息"""
        return {
            "address": self.address,
            "public_key": self.public_key_hex,
            "private_key": self.private_key_hex  # 在实际应用中，私钥应该保密
        }

    def export_private_key(self) -> str:
        """导出私钥（WIF格式）"""
        # 添加版本字节（0x80用于主网私钥）
        extended_key = PRIVATE_KEY_VERSION + self.private_key_bytes
        # 计算校验和
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        # 组合并Base58编码
        wif = base58.b58encode(extended_key + checksum).decode('utf-8')
        return wif

    @classmethod
    def from_wif(cls, wif: str) -> 'Wallet':
        """
        从WIF格式私钥创建钱包
        Args:
            wif: WIF格式的私钥
        Returns:
            Wallet: 钱包实例
        """
        # Base58解码
        decoded = base58.b58decode(wif)
        # 分离私钥和校验和
        private_key_bytes = decoded[1:-4]  # 去掉版本字节和校验和
        # 转换为16进制
        private_key_hex = private_key_bytes.hex()
        return cls(private_key_hex)

    @staticmethod
    def verify_address(address: str) -> bool:
        """
        验证地址格式是否正确
        Args:
            address: 要验证的地址
        Returns:
            bool: 地址是否有效
        """
        try:
            # Base58解码
            decoded = base58.b58decode(address)
            # 检查长度
            if len(decoded) != 25:
                return False
            # 分离校验和
            payload = decoded[:-4]
            checksum = decoded[-4:]
            # 验证校验和
            expected_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            return checksum == expected_checksum
        except Exception:
            return False

    def __str__(self) -> str:
        """钱包的字符串表示"""
        return f"钱包地址: {self.address}"


class WalletManager:
    """钱包管理器 - 管理多个钱包"""

    def __init__(self):
        """初始化钱包管理器"""
        self.wallets: Dict[str, Wallet] = {}

    def create_wallet(self, name: str) -> Wallet:
        """
        创建新钱包
        Args:
            name: 钱包名称
        Returns:
            Wallet: 新创建的钱包
        """
        if name in self.wallets:
            return self.wallets[name]

        wallet = Wallet()
        self.wallets[name] = wallet
        return wallet

    def import_wallet(self, name: str, private_key_or_wif: str) -> Wallet:
        """
        导入钱包
        Args:
            name: 钱包名称
            private_key_or_wif: 私钥（16进制）或WIF格式
        Returns:
            Wallet: 导入的钱包
        """
        try:
            # 尝试作为WIF格式导入
            if len(private_key_or_wif) > 64:
                wallet = Wallet.from_wif(private_key_or_wif)
            else:
                # 作为16进制私钥导入
                wallet = Wallet(private_key_or_wif)

            self.wallets[name] = wallet
            return wallet
        except Exception as e:
            raise ValueError(f"无效的私钥格式: {e}")

    def get_wallet(self, name: str) -> Optional[Wallet]:
        """获取指定名称的钱包"""
        return self.wallets.get(name)

    def get_wallet_by_address(self, address: str) -> Optional[Wallet]:
        """根据地址获取钱包"""
        for wallet in self.wallets.values():
            if wallet.address == address:
                return wallet
        return None

    def list_wallets(self) -> List[Dict[str, str]]:
        """
        列出所有钱包
        Returns:
            List[Dict]: 钱包信息列表
        """
        wallet_list = []
        for name, wallet in self.wallets.items():
            wallet_list.append({
                "name": name,
                "address": wallet.address,
                "public_key": wallet.public_key_hex
            })
        return wallet_list

    def export_wallet(self, name: str) -> Optional[str]:
        """
        导出钱包私钥（WIF格式）
        Args:
            name: 钱包名称
        Returns:
            str: WIF格式私钥，如果钱包不存在则返回None
        """
        wallet = self.get_wallet(name)
        if wallet:
            return wallet.export_private_key()
        return None
