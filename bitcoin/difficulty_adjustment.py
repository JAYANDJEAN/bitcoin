#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
⚖️ 比特币难度调整算法实现

比特币网络的自适应机制：
- 每2016个区块调整一次难度
- 目标是维持平均10分钟的出块时间
- 难度调整范围限制在4倍以内
- 确保网络在算力变化时保持稳定
"""

import time
import math
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class BlockHeader:
    """区块头信息"""
    height: int          # 区块高度
    timestamp: float     # 时间戳
    difficulty: float    # 难度
    target: str         # 目标值
    hash_value: str     # 区块哈希
    previous_hash: str  # 前一个区块哈希
    nonce: int          # 随机数

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'height': self.height,
            'timestamp': self.timestamp,
            'difficulty': self.difficulty,
            'target': self.target,
            'hash': self.hash_value,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }


class DifficultyAdjustment:
    """难度调整算法"""

    # 比特币常量
    ADJUSTMENT_INTERVAL = 2016      # 调整间隔（区块数）
    TARGET_TIMESPAN = 14 * 24 * 60 * 60  # 目标时间跨度（2周，秒）
    TARGET_BLOCK_TIME = 10 * 60     # 目标出块时间（10分钟，秒）
    MAX_ADJUSTMENT_FACTOR = 4       # 最大调整倍数
    MIN_ADJUSTMENT_FACTOR = 0.25    # 最小调整倍数

    def __init__(self, initial_difficulty: float = 1.0):
        """
        初始化难度调整器

        Args:
            initial_difficulty: 初始难度
        """
        self.initial_difficulty = initial_difficulty
        self.block_headers: List[BlockHeader] = []
        self.difficulty_history: List[Dict] = []

    def add_block_header(self, header: BlockHeader):
        """添加区块头"""
        self.block_headers.append(header)

    def calculate_next_difficulty(self, current_height: int) -> float:
        """
        计算下一个难度调整周期的难度

        Args:
            current_height: 当前区块高度

        Returns:
            float: 新的难度值
        """
        # 检查是否需要调整难度
        if not self.should_adjust_difficulty(current_height):
            # 不需要调整，返回当前难度
            if self.block_headers:
                return self.block_headers[-1].difficulty
            return self.initial_difficulty

        # 获取调整周期的起始和结束区块
        adjustment_start_height = current_height - self.ADJUSTMENT_INTERVAL

        # 找到对应的区块头
        start_block = self.find_block_by_height(adjustment_start_height)
        end_block = self.find_block_by_height(current_height - 1)

        if not start_block or not end_block:
            return self.block_headers[-1].difficulty if self.block_headers else self.initial_difficulty

        # 计算实际时间跨度
        actual_timespan = end_block.timestamp - start_block.timestamp

        # 计算难度调整比例
        adjustment_ratio = self.TARGET_TIMESPAN / actual_timespan

        # 限制调整范围
        adjustment_ratio = max(self.MIN_ADJUSTMENT_FACTOR,
                               min(self.MAX_ADJUSTMENT_FACTOR, adjustment_ratio))

        # 计算新难度
        current_difficulty = end_block.difficulty
        new_difficulty = current_difficulty * adjustment_ratio

        # 记录调整历史
        adjustment_info = {
            'height': current_height,
            'timestamp': time.time(),
            'old_difficulty': current_difficulty,
            'new_difficulty': new_difficulty,
            'actual_timespan': actual_timespan,
            'target_timespan': self.TARGET_TIMESPAN,
            'adjustment_ratio': adjustment_ratio,
            'reason': self._get_adjustment_reason(adjustment_ratio)
        }
        self.difficulty_history.append(adjustment_info)

        return new_difficulty

    def should_adjust_difficulty(self, height: int) -> bool:
        """
        判断是否应该调整难度

        Args:
            height: 区块高度

        Returns:
            bool: 是否需要调整
        """
        return height > 0 and height % self.ADJUSTMENT_INTERVAL == 0

    def find_block_by_height(self, height: int) -> Optional[BlockHeader]:
        """
        根据高度查找区块头

        Args:
            height: 区块高度

        Returns:
            BlockHeader: 区块头，如果不存在则返回None
        """
        for header in self.block_headers:
            if header.height == height:
                return header
        return None

    def _get_adjustment_reason(self, ratio: float) -> str:
        """获取调整原因描述"""
        if ratio > 1.5:
            return "网络算力下降，提高难度"
        elif ratio > 1.1:
            return "网络算力轻微下降，小幅提高难度"
        elif ratio < 0.67:
            return "网络算力大幅增加，降低难度"
        elif ratio < 0.9:
            return "网络算力增加，小幅降低难度"
        else:
            return "网络算力稳定，微调难度"

    def get_difficulty_statistics(self) -> Dict:
        """获取难度统计信息"""
        if not self.block_headers:
            return {}

        difficulties = [h.difficulty for h in self.block_headers]

        # 计算平均出块时间
        if len(self.block_headers) > 1:
            time_diffs = []
            for i in range(1, len(self.block_headers)):
                time_diff = self.block_headers[i].timestamp - self.block_headers[i - 1].timestamp
                time_diffs.append(time_diff)
            avg_block_time = sum(time_diffs) / len(time_diffs)
        else:
            avg_block_time = 0

        return {
            'total_blocks': len(self.block_headers),
            'current_difficulty': difficulties[-1],
            'min_difficulty': min(difficulties),
            'max_difficulty': max(difficulties),
            'avg_difficulty': sum(difficulties) / len(difficulties),
            'avg_block_time': avg_block_time,
            'target_block_time': self.TARGET_BLOCK_TIME,
            'adjustment_count': len(self.difficulty_history)
        }

    def get_adjustment_history(self) -> List[Dict]:
        """获取调整历史"""
        return self.difficulty_history.copy()

    def predict_next_adjustment(self) -> Optional[Dict]:
        """
        预测下一次难度调整

        Returns:
            Dict: 预测信息，如果无法预测则返回None
        """
        if not self.block_headers:
            return None

        current_height = self.block_headers[-1].height
        blocks_until_adjustment = self.ADJUSTMENT_INTERVAL - \
            (current_height % self.ADJUSTMENT_INTERVAL)

        if blocks_until_adjustment == self.ADJUSTMENT_INTERVAL:
            blocks_until_adjustment = 0

        # 计算当前周期的时间跨度
        cycle_start_height = current_height - (current_height % self.ADJUSTMENT_INTERVAL)
        cycle_start_block = self.find_block_by_height(cycle_start_height)

        if not cycle_start_block:
            return None

        current_cycle_time = self.block_headers[-1].timestamp - cycle_start_block.timestamp
        blocks_in_cycle = current_height - cycle_start_height + 1

        if blocks_in_cycle > 0:
            avg_time_per_block = current_cycle_time / blocks_in_cycle
            estimated_cycle_time = avg_time_per_block * self.ADJUSTMENT_INTERVAL

            # 预测调整比例
            predicted_ratio = self.TARGET_TIMESPAN / estimated_cycle_time
            predicted_ratio = max(self.MIN_ADJUSTMENT_FACTOR,
                                  min(self.MAX_ADJUSTMENT_FACTOR, predicted_ratio))

            current_difficulty = self.block_headers[-1].difficulty
            predicted_difficulty = current_difficulty * predicted_ratio

            return {
                'blocks_until_adjustment': blocks_until_adjustment,
                'current_cycle_time': current_cycle_time,
                'estimated_total_cycle_time': estimated_cycle_time,
                'avg_block_time_this_cycle': avg_time_per_block,
                'predicted_adjustment_ratio': predicted_ratio,
                'current_difficulty': current_difficulty,
                'predicted_difficulty': predicted_difficulty,
                'adjustment_direction': 'increase' if predicted_ratio > 1 else 'decrease'
            }

        return None

    def simulate_network_hashrate_change(self, hashrate_multiplier: float,
                                         num_blocks: int) -> List[BlockHeader]:
        """
        模拟网络算力变化

        Args:
            hashrate_multiplier: 算力倍数
            num_blocks: 模拟区块数量

        Returns:
            List[BlockHeader]: 模拟的区块头列表
        """
        simulated_blocks = []
        current_time = time.time()
        current_difficulty = self.block_headers[-1].difficulty if self.block_headers else self.initial_difficulty

        for i in range(num_blocks):
            # 根据算力变化调整出块时间
            actual_block_time = self.TARGET_BLOCK_TIME / hashrate_multiplier
            current_time += actual_block_time

            # 检查是否需要调整难度
            height = len(self.block_headers) + len(simulated_blocks)
            if self.should_adjust_difficulty(height):
                # 临时添加当前区块来计算新难度
                temp_header = BlockHeader(
                    height=height,
                    timestamp=current_time,
                    difficulty=current_difficulty,
                    target=self._difficulty_to_target(current_difficulty),
                    hash_value=f"simulated_hash_{height}",
                    previous_hash=f"simulated_prev_{height-1}",
                    nonce=0
                )
                self.add_block_header(temp_header)

                # 计算新难度
                current_difficulty = self.calculate_next_difficulty(height)

                # 移除临时区块
                self.block_headers.pop()

            # 创建模拟区块
            header = BlockHeader(
                height=height,
                timestamp=current_time,
                difficulty=current_difficulty,
                target=self._difficulty_to_target(current_difficulty),
                hash_value=f"simulated_hash_{height}",
                previous_hash=f"simulated_prev_{height-1}",
                nonce=0
            )
            simulated_blocks.append(header)

        return simulated_blocks

    def _difficulty_to_target(self, difficulty: float) -> str:
        """将难度转换为目标值"""
        # 简化的目标值计算
        max_target = 2**256 - 1
        target = int(max_target / difficulty)
        return f"{target:064x}"

    def save_to_file(self, filename: str):
        """保存到文件"""
        data = {
            'block_headers': [header.to_dict() for header in self.block_headers],
            'difficulty_history': self.difficulty_history,
            'statistics': self.get_difficulty_statistics(),
            'initial_difficulty': self.initial_difficulty
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filename: str):
        """从文件加载"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.initial_difficulty = data['initial_difficulty']
        self.difficulty_history = data['difficulty_history']

        # 重建区块头列表
        self.block_headers = []
        for header_data in data['block_headers']:
            header = BlockHeader(
                height=header_data['height'],
                timestamp=header_data['timestamp'],
                difficulty=header_data['difficulty'],
                target=header_data['target'],
                hash_value=header_data['hash'],
                previous_hash=header_data['previous_hash'],
                nonce=header_data['nonce']
            )
            self.block_headers.append(header)
