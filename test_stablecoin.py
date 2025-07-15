#!/usr/bin/env python3
"""
稳定币系统测试文件

测试各个组件的核心功能
"""

from stablecoin.governance import VoteType
from stablecoin.stablecoin_factory import StableCoinFactory
import time
from decimal import Decimal
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'stablecoin'))


def test_stablecoin_system():
    """测试稳定币系统"""
    print("开始稳定币系统测试...")

    # 1. 测试系统初始化
    print("\n1. 测试系统初始化")
    system = StableCoinFactory("TestUSD", "TUSD")
    assert system.name == "TestUSD"
    assert system.symbol == "TUSD"
    print("系统初始化测试通过")

    # 2. 测试抵押品管理
    print("\n2. 测试抵押品管理")

    # 存入抵押品
    success = system.collateral_manager.deposit_collateral("user1", "ETH", Decimal('10'))
    assert success

    # 检查余额
    balance = system.collateral_manager.get_collateral_balance("user1", "ETH")
    assert balance is not None
    assert balance.amount == Decimal('10')
    print("抵押品管理测试通过")

    # 3. 测试价格预言机
    print("\n3. 测试价格预言机")

    # 获取价格
    eth_price = system.price_oracle.get_price("ETH")
    assert eth_price is not None
    assert eth_price.price > 0

    # 更新价格
    success = system.price_oracle.update_price("ETH", "test_source", Decimal('2500'))
    assert success
    print("价格预言机测试通过")

    # 4. 测试稳定币头寸创建
    print("\n4. 测试稳定币头寸创建")

    position_id = system.create_collateral_backed_position(
        "user1", "ETH", Decimal('8'), Decimal('10000')
    )
    assert position_id != ""

    # 检查头寸
    position = system.stablecoin.get_position(position_id)
    assert position is not None
    assert position.owner == "user1"
    assert position.debt_amount == Decimal('10000')

    # 检查稳定币余额
    balance = system.stablecoin.balance_of("user1")
    assert balance == Decimal('10000')
    print("稳定币头寸创建测试通过")

    # 5. 测试还款和提取
    print("\n5. 测试还款和提取")

    success = system.repay_and_withdraw("user1", position_id, Decimal('5000'))
    assert success

    # 检查余额变化
    new_balance = system.stablecoin.balance_of("user1")
    assert new_balance == Decimal('5000')
    print("还款和提取测试通过")

    # 6. 测试清算系统
    print("\n6. 测试清算系统")

    # 注册清算器
    success = system.liquidation_system.register_liquidator("liquidator1")
    assert success

    # 检查清算候选
    candidates = system.liquidation_system.scan_liquidation_candidates()
    assert isinstance(candidates, list)
    print("清算系统测试通过")

    # 7. 测试治理系统
    print("\n7. 测试治理系统")

    # 检查治理代币
    voting_power = system.governance_system.get_user_voting_power("early_adopter_1")
    assert voting_power > 0

    # 创建提案
    proposal_id = system.governance_system.create_proposal(
        "early_adopter_1",
        "测试提案",
        "这是一个测试提案",
        "parameter_change",
        {"stability_fee": "0.03"}
    )
    assert proposal_id != ""
    print("治理系统测试通过")

    # 8. 测试系统健康检查
    print("\n8. 测试系统健康检查")

    health = system.system_health_check()
    assert 'system_operational' in health
    assert 'global_collateral_ratio' in health
    assert health['system_operational']
    print("系统健康检查测试通过")

    print("\n所有测试通过！稳定币系统功能正常！")
    return True


def test_edge_cases():
    """测试边缘情况"""
    print("\n测试边缘情况...")

    system = StableCoinFactory("EdgeTestUSD", "ETUSD")

    # 1. 测试抵押率不足
    print("\n1. 测试抵押率不足情况")
    system.collateral_manager.deposit_collateral("user_edge", "ETH", Decimal('1'))

    # 尝试创建抵押率过低的头寸
    position_id = system.create_collateral_backed_position(
        "user_edge", "ETH", Decimal('1'), Decimal('5000')  # 抵押率只有40%，低于150%要求
    )
    assert position_id == ""  # 应该失败
    print("抵押率不足检查通过")

    # 2. 测试余额不足
    print("\n2. 测试余额不足情况")

    # 尝试提取超过余额的抵押品
    success = system.collateral_manager.withdraw_collateral("user_edge", "ETH", Decimal('10'))
    assert success == False  # 应该失败
    print("余额不足检查通过")

    # 3. 测试无效用户操作
    print("\n3. 测试无效用户操作")

    # 尝试操作不存在的头寸
    success = system.repay_and_withdraw("user_edge", "invalid_position_id")
    assert success == False  # 应该失败
    print("无效操作检查通过")

    print("边缘情况测试通过！")


if __name__ == "__main__":
    try:
        # 运行基本功能测试
        test_stablecoin_system()

        # 运行边缘情况测试
        test_edge_cases()

        print("\n所有测试完成！稳定币系统运行良好！")

    except AssertionError as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n运行错误: {e}")
        import traceback
        traceback.print_exc()
