#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 Solidity编译器

简化版的Solidity编译器：
- 基本语法解析
- ABI生成
- 字节码生成（模拟）
- 错误检查
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


class CompilerError(Exception):
    """编译器错误"""
    pass


@dataclass
class CompilerOutput:
    """编译输出"""
    bytecode: str
    abi: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]


class SolidityCompiler:
    """Solidity编译器"""

    def __init__(self):
        self.version = "0.8.0"

    def compile(self, source_code: str) -> CompilerOutput:
        """
        编译Solidity源代码

        Args:
            source_code: Solidity源代码

        Returns:
            编译输出
        """
        warnings = []
        errors = []

        try:
            # 预处理源代码
            processed_code = self._preprocess(source_code)

            # 解析合约
            contracts = self._parse_contracts(processed_code)

            if not contracts:
                errors.append("未找到合约定义")
                return CompilerOutput("", [], warnings, errors)

            # 编译第一个合约
            contract = contracts[0]

            # 生成ABI
            abi = self._generate_abi(contract)

            # 生成字节码（模拟）
            bytecode = self._generate_bytecode(contract)

            return CompilerOutput(bytecode, abi, warnings, errors)

        except Exception as e:
            errors.append(str(e))
            return CompilerOutput("", [], warnings, errors)

    def _preprocess(self, source_code: str) -> str:
        """预处理源代码"""
        # 移除注释
        source_code = re.sub(r'//.*?\n', '\n', source_code)
        source_code = re.sub(r'/\*.*?\*/', '', source_code, flags=re.DOTALL)

        # 移除多余的空白
        source_code = re.sub(r'\s+', ' ', source_code)

        return source_code.strip()

    def _parse_contracts(self, source_code: str) -> List[Dict[str, Any]]:
        """解析合约"""
        contracts = []

        # 查找合约定义
        contract_pattern = r'contract\s+(\w+)\s*(?:is\s+[\w\s,]+)?\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        matches = re.finditer(contract_pattern, source_code)

        for match in matches:
            contract_name = match.group(1)
            contract_body = match.group(2)

            contract = {
                "name": contract_name,
                "constructor": self._parse_constructor(contract_body),
                "functions": self._parse_functions(contract_body),
                "events": self._parse_events(contract_body),
                "state_variables": self._parse_state_variables(contract_body)
            }

            contracts.append(contract)

        return contracts

    def _parse_constructor(self, contract_body: str) -> Optional[Dict[str, Any]]:
        """解析构造函数"""
        constructor_pattern = r'constructor\s*\(([^)]*)\)\s*(?:public|private|internal|external)?\s*\{'
        match = re.search(constructor_pattern, contract_body)

        if match:
            params_str = match.group(1)
            params = self._parse_parameters(params_str)

            return {
                "type": "constructor",
                "inputs": params
            }

        return None

    def _parse_functions(self, contract_body: str) -> List[Dict[str, Any]]:
        """解析函数"""
        functions = []

        function_pattern = r'function\s+(\w+)\s*\(([^)]*)\)\s*(public|private|internal|external)?\s*(view|pure|payable)?\s*(?:returns\s*\(([^)]*)\))?\s*\{'
        matches = re.finditer(function_pattern, contract_body)

        for match in matches:
            function_name = match.group(1)
            params_str = match.group(2) or ""
            visibility = match.group(3) or "public"
            state_mutability = match.group(4) or "nonpayable"
            returns_str = match.group(5) or ""

            inputs = self._parse_parameters(params_str)
            outputs = self._parse_parameters(returns_str)

            function = {
                "type": "function",
                "name": function_name,
                "inputs": inputs,
                "outputs": outputs,
                "stateMutability": state_mutability if state_mutability != "payable" else "payable",
                "payable": state_mutability == "payable"
            }

            functions.append(function)

        return functions

    def _parse_events(self, contract_body: str) -> List[Dict[str, Any]]:
        """解析事件"""
        events = []

        event_pattern = r'event\s+(\w+)\s*\(([^)]*)\)\s*;'
        matches = re.finditer(event_pattern, contract_body)

        for match in matches:
            event_name = match.group(1)
            params_str = match.group(2) or ""

            inputs = self._parse_parameters(params_str, is_event=True)

            event = {
                "type": "event",
                "name": event_name,
                "inputs": inputs
            }

            events.append(event)

        return events

    def _parse_state_variables(self, contract_body: str) -> List[Dict[str, Any]]:
        """解析状态变量"""
        variables = []

        # 简化的状态变量解析
        variable_pattern = r'(\w+)\s+(public|private|internal)?\s*(\w+)\s*(?:=\s*[^;]+)?\s*;'
        matches = re.finditer(variable_pattern, contract_body)

        for match in matches:
            var_type = match.group(1)
            visibility = match.group(2) or "internal"
            var_name = match.group(3)

            if var_type in ['uint256', 'uint', 'int', 'string', 'bool', 'address']:
                variable = {
                    "name": var_name,
                    "type": var_type,
                    "visibility": visibility
                }
                variables.append(variable)

        return variables

    def _parse_parameters(self, params_str: str, is_event: bool = False) -> List[Dict[str, str]]:
        """解析参数"""
        if not params_str.strip():
            return []

        params = []
        param_list = [p.strip() for p in params_str.split(',')]

        for param in param_list:
            if not param:
                continue

            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1]

                param_info = {
                    "name": param_name,
                    "type": param_type
                }

                if is_event and "indexed" in param:
                    param_info["indexed"] = True

                params.append(param_info)

        return params

    def _generate_abi(self, contract: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成ABI"""
        abi = []

        # 添加构造函数
        if contract["constructor"]:
            abi.append(contract["constructor"])

        # 添加函数
        abi.extend(contract["functions"])

        # 添加事件
        abi.extend(contract["events"])

        return abi

    def _generate_bytecode(self, contract: Dict[str, Any]) -> str:
        """生成字节码（模拟）"""
        # 这里是模拟的字节码生成
        # 实际的编译器会生成真正的EVM字节码

        bytecode_parts = ["608060405234801561001057600080fd5b50"]  # 基础字节码头部

        # 为每个函数添加字节码段
        for func in contract["functions"]:
            func_hash = hex(hash(func["name"]) & 0xFFFFFFFF)[2:].zfill(8)
            bytecode_parts.append(func_hash)

        # 添加构造函数字节码
        if contract["constructor"]:
            bytecode_parts.append("6001600081905550")

        # 添加结尾
        bytecode_parts.append("00a2646970667358221220")
        bytecode_parts.append("0" * 64)  # 元数据哈希占位符
        bytecode_parts.append("64736f6c63430008000033")

        return "0x" + "".join(bytecode_parts)

    def compile_standard_json(self, input_json: str) -> str:
        """编译标准JSON输入"""
        try:
            input_data = json.loads(input_json)
            sources = input_data.get("sources", {})

            output = {
                "contracts": {},
                "errors": [],
                "sources": {}
            }

            for source_name, source_info in sources.items():
                source_code = source_info.get("content", "")

                compile_result = self.compile(source_code)

                if compile_result.errors:
                    output["errors"].extend(compile_result.errors)
                else:
                    contracts = self._parse_contracts(self._preprocess(source_code))

                    for contract in contracts:
                        contract_key = f"{source_name}:{contract['name']}"
                        output["contracts"][contract_key] = {
                            "abi": compile_result.abi,
                            "evm": {
                                "bytecode": {
                                    "object": compile_result.bytecode
                                }
                            }
                        }

            return json.dumps(output, indent=2)

        except Exception as e:
            error_output = {
                "errors": [{"type": "JSONError", "message": str(e)}]
            }
            return json.dumps(error_output, indent=2)

    def get_version(self) -> str:
        """获取编译器版本"""
        return self.version

    def validate_source(self, source_code: str) -> List[str]:
        """验证源代码"""
        errors = []

        # 基本语法检查
        if "contract" not in source_code:
            errors.append("未找到合约定义")

        # 检查括号匹配
        open_braces = source_code.count('{')
        close_braces = source_code.count('}')
        if open_braces != close_braces:
            errors.append("括号不匹配")

        # 检查分号
        if source_code.count(';') == 0:
            errors.append("可能缺少分号")

        return errors

    def __str__(self) -> str:
        return f"SolidityCompiler(version={self.version})"
