"""
治理系统模块

实现去中心化治理，包括提案创建、投票和参数调整。
"""

import time
from typing import Dict, List, Optional, Set
from decimal import Decimal, getcontext
from dataclasses import dataclass, field
from enum import Enum

# 设置精度
getcontext().prec = 50


class ProposalStatus(Enum):
    """提案状态"""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    DEFEATED = "defeated"
    EXECUTED = "executed"
    EXPIRED = "expired"


class VoteType(Enum):
    """投票类型"""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """投票记录"""
    voter: str
    proposal_id: str
    vote_type: VoteType
    voting_power: Decimal
    timestamp: float

    def __post_init__(self):
        """初始化后处理"""
        self.voting_power = Decimal(str(self.voting_power))


@dataclass
class Proposal:
    """治理提案"""
    proposal_id: str
    title: str
    description: str
    proposer: str
    proposal_type: str  # "parameter_change", "upgrade", "emergency"
    parameters: Dict  # 提案参数
    voting_start: float
    voting_end: float
    execution_delay: float
    min_quorum: Decimal
    created_at: float
    status: ProposalStatus = ProposalStatus.PENDING

    # 投票统计
    votes_for: Decimal = Decimal('0')
    votes_against: Decimal = Decimal('0')
    votes_abstain: Decimal = Decimal('0')
    total_votes: Decimal = Decimal('0')

    def __post_init__(self):
        """初始化后处理"""
        self.min_quorum = Decimal(str(self.min_quorum))
        self.votes_for = Decimal(str(self.votes_for))
        self.votes_against = Decimal(str(self.votes_against))
        self.votes_abstain = Decimal(str(self.votes_abstain))
        self.total_votes = Decimal(str(self.total_votes))

    @property
    def is_active(self) -> bool:
        """检查提案是否处于投票期"""
        current_time = time.time()
        return self.voting_start <= current_time <= self.voting_end

    @property
    def is_expired(self) -> bool:
        """检查提案是否已过期"""
        return time.time() > self.voting_end

    @property
    def quorum_reached(self) -> bool:
        """检查是否达到最低投票率"""
        return self.total_votes >= self.min_quorum

    @property
    def is_succeeded(self) -> bool:
        """检查提案是否通过"""
        return (self.quorum_reached and
                self.votes_for > self.votes_against and
                self.votes_for > self.total_votes * Decimal('0.5'))


class GovernanceSystem:
    """治理系统"""

    def __init__(self, stablecoin, collateral_manager):
        self.stablecoin = stablecoin
        self.collateral_manager = collateral_manager

        # 提案管理
        self.proposals: Dict[str, Proposal] = {}
        self.proposal_votes: Dict[str, List[Vote]] = {}  # proposal_id -> votes
        self.user_votes: Dict[str, Set[str]] = {}  # user -> proposal_ids

        # 治理代币持有者
        self.governance_token_holders: Dict[str, Decimal] = {}
        self.total_governance_tokens = Decimal('1000000')  # 100万治理代币

        # 系统参数
        self.voting_period = 7 * 24 * 3600  # 7天投票期
        self.execution_delay = 2 * 24 * 3600  # 2天执行延迟
        self.min_proposal_threshold = Decimal('10000')  # 最小提案门槛
        self.min_quorum_percentage = Decimal('0.04')  # 4%最低投票率

        # 可治理的参数
        self.governable_parameters = {
            'stability_fee': 'stablecoin',
            'liquidation_ratio': 'collateral_manager',
            'liquidation_penalty': 'collateral_manager',
            'debt_ceiling': 'collateral_manager'
        }

        # 事件日志
        self.events: List[Dict] = []

        # 初始化治理代币分配
        self._init_governance_tokens()

        print("✅ 治理系统已初始化")

    def _init_governance_tokens(self):
        """初始化治理代币分配"""
        # 简单分配给几个初始持有者
        initial_holders = {
            "governance_treasury": Decimal('500000'),  # 50% 给财政部
            "early_adopter_1": Decimal('100000'),     # 10%
            "early_adopter_2": Decimal('100000'),     # 10%
            "early_adopter_3": Decimal('100000'),     # 10%
            "community_pool": Decimal('200000')       # 20% 给社区池
        }

        self.governance_token_holders = initial_holders
        print("✅ 初始化治理代币分配")

    def create_proposal(self, proposer: str, title: str, description: str,
                        proposal_type: str, parameters: Dict) -> str:
        """创建提案"""
        try:
            # 检查提案权限
            proposer_tokens = self.governance_token_holders.get(proposer, Decimal('0'))
            if proposer_tokens < self.min_proposal_threshold:
                raise ValueError(f"提案者代币不足，需要至少 {self.min_proposal_threshold}")

            # 生成提案ID
            proposal_id = self._generate_proposal_id()

            # 计算投票时间
            current_time = time.time()
            voting_start = current_time + 3600  # 1小时后开始投票
            voting_end = voting_start + self.voting_period

            # 计算最低投票率
            min_quorum = self.total_governance_tokens * self.min_quorum_percentage

            # 创建提案
            proposal = Proposal(
                proposal_id=proposal_id,
                title=title,
                description=description,
                proposer=proposer,
                proposal_type=proposal_type,
                parameters=parameters,
                voting_start=voting_start,
                voting_end=voting_end,
                execution_delay=self.execution_delay,
                min_quorum=min_quorum,
                created_at=current_time
            )

            # 存储提案
            self.proposals[proposal_id] = proposal
            self.proposal_votes[proposal_id] = []

            # 记录事件
            event = {
                'type': 'proposal_created',
                'proposal_id': proposal_id,
                'title': title,
                'proposer': proposer,
                'timestamp': current_time
            }
            self.events.append(event)

            print(f"✅ 创建提案: {title} (ID: {proposal_id})")
            return proposal_id

        except Exception as e:
            print(f"❌ 创建提案失败: {e}")
            return ""

    def vote_on_proposal(self, voter: str, proposal_id: str, vote_type: VoteType) -> bool:
        """对提案投票"""
        try:
            # 检查提案是否存在
            if proposal_id not in self.proposals:
                raise ValueError(f"提案 {proposal_id} 不存在")

            proposal = self.proposals[proposal_id]

            # 检查投票期
            if not proposal.is_active:
                raise ValueError("提案不在投票期内")

            # 检查是否已经投票
            if voter in self.user_votes and proposal_id in self.user_votes[voter]:
                raise ValueError("已经对此提案投票")

            # 获取投票权重
            voting_power = self.governance_token_holders.get(voter, Decimal('0'))
            if voting_power <= 0:
                raise ValueError("没有投票权")

            # 创建投票记录
            vote = Vote(
                voter=voter,
                proposal_id=proposal_id,
                vote_type=vote_type,
                voting_power=voting_power,
                timestamp=time.time()
            )

            # 更新提案投票统计
            if vote_type == VoteType.FOR:
                proposal.votes_for += voting_power
            elif vote_type == VoteType.AGAINST:
                proposal.votes_against += voting_power
            else:  # ABSTAIN
                proposal.votes_abstain += voting_power

            proposal.total_votes += voting_power

            # 存储投票记录
            self.proposal_votes[proposal_id].append(vote)

            if voter not in self.user_votes:
                self.user_votes[voter] = set()
            self.user_votes[voter].add(proposal_id)

            # 记录事件
            event = {
                'type': 'vote_cast',
                'voter': voter,
                'proposal_id': proposal_id,
                'vote_type': vote_type.value,
                'voting_power': voting_power,
                'timestamp': time.time()
            }
            self.events.append(event)

            print(f"✅ {voter} 对提案 {proposal_id} 投票: {vote_type.value}")
            return True

        except Exception as e:
            print(f"❌ 投票失败: {e}")
            return False

    def update_proposal_status(self, proposal_id: str) -> bool:
        """更新提案状态"""
        try:
            if proposal_id not in self.proposals:
                return False

            proposal = self.proposals[proposal_id]
            current_time = time.time()

            # 更新状态逻辑
            if proposal.status == ProposalStatus.PENDING:
                if proposal.is_active:
                    proposal.status = ProposalStatus.ACTIVE

            elif proposal.status == ProposalStatus.ACTIVE:
                if proposal.is_expired:
                    if proposal.is_succeeded:
                        proposal.status = ProposalStatus.SUCCEEDED
                    else:
                        proposal.status = ProposalStatus.DEFEATED

            return True

        except Exception as e:
            print(f"❌ 更新提案状态失败: {e}")
            return False

    def execute_proposal(self, proposal_id: str) -> bool:
        """执行提案"""
        try:
            if proposal_id not in self.proposals:
                raise ValueError(f"提案 {proposal_id} 不存在")

            proposal = self.proposals[proposal_id]

            # 检查提案状态
            if proposal.status != ProposalStatus.SUCCEEDED:
                raise ValueError("提案未通过或已执行")

            # 检查执行延迟
            if time.time() < proposal.voting_end + proposal.execution_delay:
                raise ValueError("提案还在执行延迟期内")

            # 执行提案
            success = self._execute_proposal_changes(proposal)

            if success:
                proposal.status = ProposalStatus.EXECUTED

                # 记录事件
                event = {
                    'type': 'proposal_executed',
                    'proposal_id': proposal_id,
                    'timestamp': time.time()
                }
                self.events.append(event)

                print(f"✅ 提案 {proposal_id} 执行成功")
                return True
            else:
                print(f"❌ 提案 {proposal_id} 执行失败")
                return False

        except Exception as e:
            print(f"❌ 执行提案失败: {e}")
            return False

    def _execute_proposal_changes(self, proposal: Proposal) -> bool:
        """执行提案中的具体变更"""
        try:
            if proposal.proposal_type == "parameter_change":
                return self._execute_parameter_changes(proposal.parameters)
            elif proposal.proposal_type == "upgrade":
                return self._execute_upgrade(proposal.parameters)
            elif proposal.proposal_type == "emergency":
                return self._execute_emergency_action(proposal.parameters)
            else:
                print(f"❌ 未知的提案类型: {proposal.proposal_type}")
                return False

        except Exception as e:
            print(f"❌ 执行提案变更失败: {e}")
            return False

    def _execute_parameter_changes(self, parameters: Dict) -> bool:
        """执行参数变更"""
        try:
            for param_name, new_value in parameters.items():
                if param_name in self.governable_parameters:
                    target_system = self.governable_parameters[param_name]

                    if target_system == "stablecoin":
                        setattr(self.stablecoin, param_name, Decimal(str(new_value)))
                    elif target_system == "collateral_manager":
                        # 更新所有抵押品类型的参数
                        for collateral_type in self.collateral_manager.collateral_types.values():
                            setattr(collateral_type, param_name, Decimal(str(new_value)))

                    print(f"✅ 更新参数 {param_name} = {new_value}")
                else:
                    print(f"⚠️ 参数 {param_name} 不可治理")

            return True

        except Exception as e:
            print(f"❌ 执行参数变更失败: {e}")
            return False

    def _execute_upgrade(self, parameters: Dict) -> bool:
        """执行系统升级"""
        # 这里应该实现具体的升级逻辑
        print("✅ 执行系统升级（模拟）")
        return True

    def _execute_emergency_action(self, parameters: Dict) -> bool:
        """执行紧急操作"""
        # 这里应该实现紧急操作逻辑，如暂停系统等
        print("✅ 执行紧急操作（模拟）")
        return True

    def _generate_proposal_id(self) -> str:
        """生成提案ID"""
        import hashlib
        data = f"proposal_{time.time()}_{len(self.proposals)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """获取提案信息"""
        return self.proposals.get(proposal_id)

    def get_active_proposals(self) -> List[Proposal]:
        """获取活跃提案"""
        active_proposals = []
        for proposal in self.proposals.values():
            self.update_proposal_status(proposal.proposal_id)
            if proposal.status == ProposalStatus.ACTIVE:
                active_proposals.append(proposal)
        return active_proposals

    def get_user_voting_power(self, user: str) -> Decimal:
        """获取用户投票权重"""
        return self.governance_token_holders.get(user, Decimal('0'))

    def delegate_voting_power(self, delegator: str, delegate: str, amount: Decimal) -> bool:
        """委托投票权（简化实现）"""
        try:
            amount = Decimal(str(amount))

            if delegator not in self.governance_token_holders:
                raise ValueError("委托人没有治理代币")

            if self.governance_token_holders[delegator] < amount:
                raise ValueError("委托数量超过持有量")

            # 转移投票权
            self.governance_token_holders[delegator] -= amount

            if delegate not in self.governance_token_holders:
                self.governance_token_holders[delegate] = Decimal('0')
            self.governance_token_holders[delegate] += amount

            print(f"✅ {delegator} 向 {delegate} 委托 {amount} 投票权")
            return True

        except Exception as e:
            print(f"❌ 委托投票权失败: {e}")
            return False

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        active_proposals = len([p for p in self.proposals.values()
                                if p.status == ProposalStatus.ACTIVE])
        executed_proposals = len([p for p in self.proposals.values()
                                  if p.status == ProposalStatus.EXECUTED])

        return {
            'total_proposals': len(self.proposals),
            'active_proposals': active_proposals,
            'executed_proposals': executed_proposals,
            'total_governance_tokens': self.total_governance_tokens,
            'token_holders': len(self.governance_token_holders),
            'voting_period_days': self.voting_period / (24 * 3600),
            'min_proposal_threshold': self.min_proposal_threshold,
            'min_quorum_percentage': self.min_quorum_percentage
        }

    def print_status(self):
        """打印系统状态"""
        stats = self.get_system_stats()
        print(f"\n=== 治理系统状态 ===")
        print(f"提案总数: {stats['total_proposals']}")
        print(f"活跃提案: {stats['active_proposals']}")
        print(f"已执行提案: {stats['executed_proposals']}")
        print(f"治理代币总量: {stats['total_governance_tokens']}")
        print(f"代币持有者数量: {stats['token_holders']}")
        print(f"投票期: {stats['voting_period_days']}天")
        print(f"提案门槛: {stats['min_proposal_threshold']}")
        print(f"最低投票率: {stats['min_quorum_percentage']:.1%}")
