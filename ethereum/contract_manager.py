#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📋 智能合约管理器

提供合约的注册、查找、版本管理等功能：
- 合约注册表
- 版本控制
- 合约工厂
- 批量操作
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from .smart_contract import SmartContract, ContractState
from .virtual_machine import EthereumVM, VMError


@dataclass
class ContractInfo:
    """合约信息"""
    name: str
    version: str
    address: str
    deployer: str
    deployment_time: int
    description: str = ""
    tags: List[str] = field(default_factory=list)


class ContractRegistry:
    """合约注册表"""

    def __init__(self):
        self.contracts: Dict[str, ContractInfo] = {}  # address -> info
        self.name_index: Dict[str, List[str]] = {}    # name -> addresses
        self.tag_index: Dict[str, List[str]] = {}     # tag -> addresses

    def register(self, contract_info: ContractInfo):
        """注册合约"""
        address = contract_info.address
        self.contracts[address] = contract_info

        # 更新名称索引
        name = contract_info.name
        if name not in self.name_index:
            self.name_index[name] = []
        self.name_index[name].append(address)

        # 更新标签索引
        for tag in contract_info.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(address)

    def unregister(self, address: str):
        """注销合约"""
        if address not in self.contracts:
            return False

        contract_info = self.contracts[address]

        # 从名称索引中移除
        name = contract_info.name
        if name in self.name_index:
            self.name_index[name].remove(address)
            if not self.name_index[name]:
                del self.name_index[name]

        # 从标签索引中移除
        for tag in contract_info.tags:
            if tag in self.tag_index:
                self.tag_index[tag].remove(address)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]

        # 移除合约信息
        del self.contracts[address]
        return True

    def find_by_name(self, name: str, version: str = None) -> List[ContractInfo]:
        """按名称查找合约"""
        addresses = self.name_index.get(name, [])
        contracts = [self.contracts[addr] for addr in addresses]

        if version:
            contracts = [c for c in contracts if c.version == version]

        return contracts

    def find_by_tag(self, tag: str) -> List[ContractInfo]:
        """按标签查找合约"""
        addresses = self.tag_index.get(tag, [])
        return [self.contracts[addr] for addr in addresses]

    def get_info(self, address: str) -> Optional[ContractInfo]:
        """获取合约信息"""
        return self.contracts.get(address)

    def list_all(self) -> List[ContractInfo]:
        """列出所有合约"""
        return list(self.contracts.values())

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_contracts": len(self.contracts),
            "unique_names": len(self.name_index),
            "total_tags": len(self.tag_index),
            "contracts_by_name": {
                name: len(addresses)
                for name, addresses in self.name_index.items()
            },
            "contracts_by_tag": {
                tag: len(addresses)
                for tag, addresses in self.tag_index.items()
            }
        }


class ContractManager:
    """合约管理器"""

    def __init__(self, vm: EthereumVM = None):
        self.vm = vm or EthereumVM()
        self.registry = ContractRegistry()
        self.templates: Dict[str, Dict[str, Any]] = {}

    def register_template(self, name: str, template: Dict[str, Any]):
        """注册合约模板"""
        self.templates[name] = template

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """获取合约模板"""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return list(self.templates.keys())

    def create_contract_from_template(self, template_name: str,
                                      constructor_args: List[Any] = None) -> SmartContract:
        """从模板创建合约"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")

        contract = SmartContract(
            contract_code=template.get("code", ""),
            abi=template.get("abi", [])
        )

        return contract

    def deploy_contract(self, contract: SmartContract, deployer: str,
                        constructor_args: List[Any] = None,
                        contract_name: str = "", version: str = "1.0.0",
                        description: str = "", tags: List[str] = None) -> str:
        """部署合约并注册"""
        # 部署合约
        address = self.vm.deploy_contract(contract, constructor_args, deployer)

        # 注册到注册表
        contract_info = ContractInfo(
            name=contract_name or f"Contract_{address[:8]}",
            version=version,
            address=address,
            deployer=deployer,
            deployment_time=int(time.time()),
            description=description,
            tags=tags or []
        )

        self.registry.register(contract_info)

        return address

    def deploy_from_template(self, template_name: str, deployer: str,
                             constructor_args: List[Any] = None,
                             contract_name: str = "", version: str = "1.0.0",
                             description: str = "", tags: List[str] = None) -> str:
        """从模板部署合约"""
        contract = self.create_contract_from_template(template_name, constructor_args)

        return self.deploy_contract(
            contract, deployer, constructor_args,
            contract_name or template_name, version, description, tags
        )

    def call_contract(self, address: str, function_name: str,
                      args: List[Any] = None, caller: str = "0x0",
                      value: int = 0) -> Any:
        """调用合约函数"""
        return self.vm.call_contract(address, function_name, args, caller, value)

    def get_contract(self, address: str) -> Optional[SmartContract]:
        """获取合约实例"""
        return self.vm.get_contract(address)

    def get_contract_info(self, address: str) -> Optional[ContractInfo]:
        """获取合约注册信息"""
        return self.registry.get_info(address)

    def find_contracts(self, name: str = None, tag: str = None,
                       version: str = None) -> List[ContractInfo]:
        """查找合约"""
        if name:
            return self.registry.find_by_name(name, version)
        elif tag:
            return self.registry.find_by_tag(tag)
        else:
            return self.registry.list_all()

    def upgrade_contract(self, old_address: str, new_contract: SmartContract,
                         deployer: str, version: str) -> str:
        """升级合约"""
        # 获取旧合约信息
        old_info = self.registry.get_info(old_address)
        if not old_info:
            raise ValueError(f"合约不存在: {old_address}")

        # 部署新合约
        new_address = self.deploy_contract(
            new_contract, deployer, None,
            old_info.name, version,
            f"升级自 {old_info.version}",
            old_info.tags + ["upgrade"]
        )

        return new_address

    def batch_call(self, calls: List[Dict[str, Any]]) -> List[Any]:
        """批量调用合约函数"""
        results = []

        for call in calls:
            try:
                result = self.call_contract(
                    call.get("address"),
                    call.get("function"),
                    call.get("args", []),
                    call.get("caller", "0x0"),
                    call.get("value", 0)
                )
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return results

    def export_contracts(self, addresses: List[str] = None) -> Dict[str, Any]:
        """导出合约数据"""
        if addresses is None:
            addresses = list(self.registry.contracts.keys())

        export_data = {
            "timestamp": int(time.time()),
            "contracts": {}
        }

        for address in addresses:
            contract = self.vm.get_contract(address)
            contract_info = self.registry.get_info(address)

            if contract and contract_info:
                export_data["contracts"][address] = {
                    "info": {
                        "name": contract_info.name,
                        "version": contract_info.version,
                        "deployer": contract_info.deployer,
                        "deployment_time": contract_info.deployment_time,
                        "description": contract_info.description,
                        "tags": contract_info.tags
                    },
                    "contract": contract.to_dict()
                }

        return export_data

    def import_contracts(self, import_data: Dict[str, Any]):
        """导入合约数据"""
        for address, data in import_data.get("contracts", {}).items():
            # 恢复合约
            contract = SmartContract.from_dict(data["contract"])
            self.vm.contracts[address] = contract

            # 恢复注册信息
            info_data = data["info"]
            contract_info = ContractInfo(
                name=info_data["name"],
                version=info_data["version"],
                address=address,
                deployer=info_data["deployer"],
                deployment_time=info_data["deployment_time"],
                description=info_data["description"],
                tags=info_data["tags"]
            )
            self.registry.register(contract_info)

    def get_manager_statistics(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        registry_stats = self.registry.get_statistics()
        vm_stats = self.vm.get_vm_state()

        return {
            "registry": registry_stats,
            "vm": vm_stats,
            "templates": len(self.templates)
        }

    def cleanup_destroyed_contracts(self) -> int:
        """清理已销毁的合约"""
        destroyed_count = 0
        addresses_to_remove = []

        for address, contract in self.vm.contracts.items():
            if contract.state == ContractState.DESTROYED:
                addresses_to_remove.append(address)

        for address in addresses_to_remove:
            del self.vm.contracts[address]
            self.registry.unregister(address)
            destroyed_count += 1

        return destroyed_count

    def __str__(self) -> str:
        return f"ContractManager(contracts={len(self.registry.contracts)}, templates={len(self.templates)})"
