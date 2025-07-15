#!/usr/bin/env python3
"""
稳定币系统演示

展示完整的稳定币系统功能，包括：
- 系统初始化
- 抵押品管理
- 稳定币铸造和销毁
- 清算机制
- 治理投票
- 价格模拟
"""

from decimal import Decimal
import time

from .stablecoin_factory import StableCoinFactory
from .governance import VoteType


def main():
    """主演示函数"""

    print("🚀 欢迎使用去中心化稳定币系统演示！")
    print("=" * 60)

    # 1. 初始化稳定币系统
    print("\n【第一步】初始化稳定币系统")
    stablecoin_system = StableCoinFactory("DecentralizedUSD", "DUSD")

    # 等待一下让用户看到输出
    time.sleep(2)

    # 2. 设置测试用户
    print("\n【第二步】设置测试用户")
    users = {
        "alice": "用户Alice - 早期使用者",
        "bob": "用户Bob - 投资者",
        "charlie": "用户Charlie - 清算器",
        "dao_treasury": "DAO财政部"
    }

    for user, desc in users.items():
        print(f"👤 {desc}")

    # 3. 为用户充值抵押品
    print("\n【第三步】为用户充值抵押品")

    # Alice 存入 ETH
    stablecoin_system.collateral_manager.deposit_collateral("alice", "ETH", Decimal('10'))
    stablecoin_system.collateral_manager.deposit_collateral("alice", "BTC", Decimal('0.5'))

    # Bob 存入 USDC
    stablecoin_system.collateral_manager.deposit_collateral("bob", "USDC", Decimal('50000'))
    stablecoin_system.collateral_manager.deposit_collateral("bob", "ETH", Decimal('25'))

    # Charlie 存入各种抵押品
    stablecoin_system.collateral_manager.deposit_collateral("charlie", "ETH", Decimal('5'))
    stablecoin_system.collateral_manager.deposit_collateral("charlie", "BTC", Decimal('0.2'))

    time.sleep(1)

    # 4. 创建稳定币头寸
    print("\n【第四步】创建稳定币头寸")

    # Alice 用 ETH 抵押借出 DUSD
    alice_position1 = stablecoin_system.create_collateral_backed_position(
        "alice", "ETH", Decimal('8'), Decimal('10000')  # 抵押率 160%
    )

    # Alice 用 BTC 抵押借出 DUSD
    alice_position2 = stablecoin_system.create_collateral_backed_position(
        "alice", "BTC", Decimal('0.3'), Decimal('10000')  # 抵押率 135%
    )

    # Bob 用 USDC 抵押借出 DUSD
    bob_position = stablecoin_system.create_collateral_backed_position(
        "bob", "USDC", Decimal('31500'), Decimal('30000')  # 抵押率 105%
    )

    time.sleep(1)

    # 5. 注册清算器
    print("\n【第五步】注册清算器")
    stablecoin_system.liquidation_system.register_liquidator("charlie")

    # 给清算器一些稳定币用于清算
    stablecoin_system.stablecoin.mint("charlie", Decimal('5000'))

    # 6. 展示系统状态
    print("\n【第六步】系统当前状态")
    stablecoin_system.print_full_status()

    time.sleep(2)

    # 7. 模拟价格下跌触发清算
    print("\n【第七步】模拟市场价格下跌")
    price_changes = {
        "ETH": Decimal('-0.25'),  # ETH 下跌 25%
        "BTC": Decimal('-0.20'),  # BTC 下跌 20%
    }

    stablecoin_system.simulate_market_movement(price_changes)

    time.sleep(1)

    # 8. 检查清算候选
    print("\n【第八步】检查清算情况")
    liquidation_monitoring = stablecoin_system.liquidation_system.monitor_positions()

    if liquidation_monitoring['liquidation_candidates'] > 0:
        print(f"⚠️ 发现 {liquidation_monitoring['liquidation_candidates']} 个需要清算的头寸")

        # 手动执行一次清算
        candidates = stablecoin_system.liquidation_system.scan_liquidation_candidates()
        if candidates:
            most_urgent = candidates[0]
            liquidation_id = stablecoin_system.liquidation_system.liquidate_position(
                "charlie", most_urgent.position_id
            )
            if liquidation_id:
                print(f"✅ 成功清算头寸，清算ID: {liquidation_id}")

    time.sleep(1)

    # 9. 创建治理提案
    print("\n【第九步】创建治理提案")

    # 提案调整稳定费
    proposal_id = stablecoin_system.governance_system.create_proposal(
        proposer="early_adopter_1",
        title="调整系统稳定费率",
        description="建议将稳定费从2%调整为2.5%以提高系统收入",
        proposal_type="parameter_change",
        parameters={"stability_fee": "0.025"}
    )

    if proposal_id:
        print(f"✅ 创建提案成功: {proposal_id}")

        # 模拟投票
        print("\n【第十步】治理投票")
        stablecoin_system.governance_system.vote_on_proposal(
            "early_adopter_1", proposal_id, VoteType.FOR
        )
        stablecoin_system.governance_system.vote_on_proposal(
            "early_adopter_2", proposal_id, VoteType.FOR
        )
        stablecoin_system.governance_system.vote_on_proposal(
            "governance_treasury", proposal_id, VoteType.AGAINST
        )

    time.sleep(1)

    # 10. 用户操作 - 还款和提取
    print("\n【第十一步】用户还款操作")

    # Alice 部分还款
    if alice_position1:
        alice_balance = stablecoin_system.stablecoin.balance_of("alice")
        if alice_balance >= Decimal('5000'):
            success = stablecoin_system.repay_and_withdraw(
                "alice", alice_position1,
                repay_amount=Decimal('5000'),
                withdraw_amount=Decimal('2')
            )
            if success:
                print("✅ Alice 成功还款并提取部分抵押品")

    time.sleep(1)

    # 11. 显示用户概览
    print("\n【第十二步】用户资产概览")
    for user in ["alice", "bob", "charlie"]:
        overview = stablecoin_system.get_user_overview(user)
        print(f"\n👤 {user.upper()} 的资产概览:")
        print(f"   稳定币余额: {overview['stablecoin_balance']} DUSD")
        print(f"   抵押品数量: {len(overview['collaterals'])}")
        print(f"   持有头寸数: {len(overview['positions'])}")
        print(f"   治理代币: {overview['governance_tokens']}")
        print(f"   清算器身份: {'是' if overview['liquidator_registered'] else '否'}")

    # 12. 最终系统健康检查
    print("\n【第十三步】最终系统状态")
    health = stablecoin_system.system_health_check()

    print(f"🏥 系统健康度: {health.get('risk_level', 'UNKNOWN')}")
    print(f"📊 全局抵押率: {health.get('global_collateral_ratio', 0):.2f}")
    print(f"💰 总抵押品价值: ${health.get('total_collateral_value', 0)}")
    print(f"💸 总债务: {health.get('total_debt', 0)} DUSD")
    print(f"⚠️ 清算候选: {health.get('liquidation_candidates', 0)}")
    print(f"🏃 紧急清算: {health.get('urgent_liquidations', 0)}")

    # 13. 演示结束
    print(f"\n{'='*60}")
    print("🎉 稳定币系统演示完成！")
    print("💡 主要功能演示:")
    print("   ✅ 多种抵押品支持 (ETH, BTC, USDC)")
    print("   ✅ 稳定币铸造和销毁")
    print("   ✅ 实时价格监控和聚合")
    print("   ✅ 自动清算机制")
    print("   ✅ 去中心化治理")
    print("   ✅ 系统健康监控")
    print("   ✅ 用户友好的接口")
    print(f"{'='*60}")


def run_stress_test():
    """压力测试"""
    print("\n🔥 运行系统压力测试...")

    system = StableCoinFactory("StressTestUSD", "STUSD")

    # 创建大量用户和头寸
    print("📈 创建大量用户头寸...")
    for i in range(20):
        user = f"user_{i:02d}"

        # 存入抵押品
        system.collateral_manager.deposit_collateral(user, "ETH", Decimal('10'))

        # 创建头寸
        position_id = system.create_collateral_backed_position(
            user, "ETH", Decimal('8'), Decimal('10000')
        )

        if i % 5 == 0:
            print(f"   已创建 {i+1} 个头寸...")

    # 模拟极端市场条件
    print("\n📉 模拟极端市场下跌...")
    extreme_changes = {
        "ETH": Decimal('-0.40'),  # ETH 暴跌 40%
        "BTC": Decimal('-0.35'),  # BTC 暴跌 35%
    }

    system.simulate_market_movement(extreme_changes)

    # 检查系统响应
    health = system.system_health_check()
    print(f"\n🏥 极端条件下系统状态:")
    print(f"   风险等级: {health.get('risk_level', 'UNKNOWN')}")
    print(f"   清算候选: {health.get('liquidation_candidates', 0)}")
    print(f"   系统运行: {'正常' if health.get('system_operational', False) else '异常'}")

    print("✅ 压力测试完成！")


if __name__ == "__main__":
    try:
        # 运行主演示
        main()

        # 询问是否运行压力测试
        print("\n❓ 是否运行压力测试？(y/n): ", end="")
        # 在实际环境中，这里会等待用户输入
        # 为了自动演示，我们跳过用户交互
        print("跳过压力测试（自动演示模式）")

        print("\n🎯 演示程序结束！")
        print("💡 您可以修改参数重新运行，或查看各个模块的详细实现。")

    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
