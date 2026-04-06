"""人生目标决策 Demo 运行模块。

这个模块把 README 中展示的人生目标决策流程做成可复用的本地 Demo：
- 脚本可以直接调用
- CLI 子命令可以直接调用
- 测试也可以复用同一套逻辑

支持全部 6 个领域: career, finance, health, education, lifestyle, relationship。
每个领域有独立的预置历史数据和决策选项。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from openharness.tools.base import ToolExecutionContext
from openharness.tools.lifegoal_tool import LifeGoalTool, LifeGoalToolInput
from openharness.tools.recall_decisions_tool import RecallDecisionsInput, RecallDecisionsTool
from openharness.tools.recall_preferences_tool import RecallPreferencesInput, RecallPreferencesTool
from openharness.tools.save_decision_tool import SaveDecisionInput, SaveDecisionTool
from velaris_agent.memory.decision_memory import DecisionMemory
from velaris_agent.memory.types import DecisionRecord


# ---------------------------------------------------------------------------
# 全部 6 个领域的 Demo 配置
# ---------------------------------------------------------------------------

# 每个领域的配置: 历史偏好种子 + 当前决策选项 + 查询语句
DOMAIN_DEMOS: dict[str, dict[str, Any]] = {
    "career": {
        "query": "现在有两个 offer，一个钱多一个成长更好，我该怎么选",
        "constraints": ["下半年希望转管理岗", "不希望长期 996"],
        "risk_tolerance": "moderate",
        "seed_history": {
            "query": "两个 offer 怎么选，短期薪资和长期成长怎么平衡",
            "recommended": {"id": "high-pay", "label": "高薪但平台一般"},
            "user_choice": {"id": "growth-track", "label": "薪资一般但成长更好"},
            "user_feedback": 4.6,
            "scores": [
                {"id": "high-pay", "scores": {"income": 0.95, "growth": 0.45, "fulfillment": 0.55, "stability": 0.7, "work_life_balance": 0.4}},
                {"id": "growth-track", "scores": {"income": 0.65, "growth": 0.92, "fulfillment": 0.88, "stability": 0.62, "work_life_balance": 0.74}},
            ],
            "weights_used": {"income": 0.25, "growth": 0.25, "fulfillment": 0.2, "stability": 0.15, "work_life_balance": 0.15},
        },
        "options": [
            {
                "id": "offer-a", "label": "Offer A: 大厂高薪岗",
                "dimensions": {"income": 0.93, "growth": 0.58, "fulfillment": 0.6, "stability": 0.82, "work_life_balance": 0.35},
                "risks": ["加班强度较高", "岗位成长空间有限"],
                "opportunities": ["短期现金流显著提升"],
            },
            {
                "id": "offer-b", "label": "Offer B: 成长型核心岗位",
                "dimensions": {"income": 0.7, "growth": 0.94, "fulfillment": 0.88, "stability": 0.68, "work_life_balance": 0.76},
                "risks": ["短期收入不如 Offer A"],
                "opportunities": ["更快进入核心业务", "更适合转管理岗"],
            },
        ],
    },
    "finance": {
        "query": "手上有 50 万闲钱，该买理财还是提前还房贷",
        "constraints": ["房贷利率 3.85%", "还有 18 年贷款", "家庭月支出 2 万"],
        "risk_tolerance": "conservative",
        "seed_history": {
            "query": "年终奖怎么处理，买基金还是存定期",
            "recommended": {"id": "fund-mix", "label": "混合基金组合"},
            "user_choice": {"id": "fixed-deposit", "label": "银行定期存款"},
            "user_feedback": 4.2,
            "scores": [
                {"id": "fund-mix", "scores": {"expected_return": 0.75, "risk": 0.45, "liquidity": 0.65, "tax_efficiency": 0.7, "simplicity": 0.4}},
                {"id": "fixed-deposit", "scores": {"expected_return": 0.35, "risk": 0.92, "liquidity": 0.55, "tax_efficiency": 0.85, "simplicity": 0.95}},
            ],
            "weights_used": {"expected_return": 0.3, "risk": 0.25, "liquidity": 0.2, "tax_efficiency": 0.15, "simplicity": 0.1},
        },
        "options": [
            {
                "id": "repay-loan", "label": "提前还房贷",
                "dimensions": {"expected_return": 0.38, "risk": 0.95, "liquidity": 0.15, "tax_efficiency": 0.6, "simplicity": 0.9},
                "risks": ["资金流动性大幅降低", "机会成本"],
                "opportunities": ["确定性节省利息支出", "减轻月供心理压力"],
            },
            {
                "id": "wealth-mgmt", "label": "稳健理财组合 (国债+大额存单)",
                "dimensions": {"expected_return": 0.45, "risk": 0.88, "liquidity": 0.7, "tax_efficiency": 0.75, "simplicity": 0.7},
                "risks": ["收益不稳定", "需要定期关注"],
                "opportunities": ["保持流动性", "利差收益"],
            },
            {
                "id": "split-plan", "label": "一半还贷一半理财",
                "dimensions": {"expected_return": 0.42, "risk": 0.9, "liquidity": 0.45, "tax_efficiency": 0.68, "simplicity": 0.65},
                "risks": ["两边都没做到极致"],
                "opportunities": ["兼顾安全感和灵活性"],
            },
        ],
    },
    "health": {
        "query": "想开始锻炼身体，跑步和游泳选哪个更适合我",
        "constraints": ["膝盖有轻微损伤", "每周最多 4 次", "附近有游泳馆"],
        "risk_tolerance": "moderate",
        "seed_history": {
            "query": "需要减重，低碳饮食和间歇性断食选哪个",
            "recommended": {"id": "low-carb", "label": "低碳饮食"},
            "user_choice": {"id": "low-carb", "label": "低碳饮食"},
            "user_feedback": 3.8,
            "scores": [
                {"id": "low-carb", "scores": {"effectiveness": 0.75, "sustainability": 0.6, "cost": 0.7, "enjoyment": 0.5, "time_required": 0.8}},
                {"id": "intermittent-fast", "scores": {"effectiveness": 0.7, "sustainability": 0.5, "cost": 0.95, "enjoyment": 0.35, "time_required": 0.9}},
            ],
            "weights_used": {"effectiveness": 0.3, "sustainability": 0.25, "cost": 0.15, "enjoyment": 0.2, "time_required": 0.1},
        },
        "options": [
            {
                "id": "running", "label": "跑步 (户外/跑步机)",
                "dimensions": {"effectiveness": 0.82, "sustainability": 0.65, "cost": 0.9, "enjoyment": 0.6, "time_required": 0.75},
                "risks": ["膝盖损伤可能加重", "天气影响户外跑"],
                "opportunities": ["入门门槛最低", "随时随地"],
            },
            {
                "id": "swimming", "label": "游泳",
                "dimensions": {"effectiveness": 0.85, "sustainability": 0.8, "cost": 0.5, "enjoyment": 0.75, "time_required": 0.6},
                "risks": ["需要固定场地和时间", "月卡费用"],
                "opportunities": ["对膝盖友好", "全身运动效果好"],
            },
        ],
    },
    "education": {
        "query": "要不要花 3 万报个 AI 培训班，还是自学",
        "constraints": ["工作日晚上有 2 小时", "有 Python 基础", "目标是转 AI 岗"],
        "risk_tolerance": "moderate",
        "seed_history": {
            "query": "PMP 证书值不值得考",
            "recommended": {"id": "skip-pmp", "label": "暂时不考 PMP"},
            "user_choice": {"id": "take-pmp", "label": "考 PMP"},
            "user_feedback": 3.5,
            "scores": [
                {"id": "take-pmp", "scores": {"career_impact": 0.55, "cost": 0.4, "time_investment": 0.35, "interest_alignment": 0.3, "credential_value": 0.75}},
                {"id": "skip-pmp", "scores": {"career_impact": 0.45, "cost": 0.95, "time_investment": 0.95, "interest_alignment": 0.8, "credential_value": 0.1}},
            ],
            "weights_used": {"career_impact": 0.3, "cost": 0.2, "time_investment": 0.2, "interest_alignment": 0.2, "credential_value": 0.1},
        },
        "options": [
            {
                "id": "ai-bootcamp", "label": "报名 AI 培训班",
                "dimensions": {"career_impact": 0.8, "cost": 0.3, "time_investment": 0.5, "interest_alignment": 0.85, "credential_value": 0.65},
                "risks": ["3 万投入不小", "培训质量参差不齐"],
                "opportunities": ["系统化学习路径", "有人带少走弯路", "结业证书"],
            },
            {
                "id": "self-study", "label": "自学 (Coursera + 开源项目)",
                "dimensions": {"career_impact": 0.65, "cost": 0.9, "time_investment": 0.4, "interest_alignment": 0.9, "credential_value": 0.35},
                "risks": ["缺乏系统性", "容易中途放弃", "无人答疑"],
                "opportunities": ["成本极低", "节奏自由", "实战项目积累"],
            },
        ],
    },
    "lifestyle": {
        "query": "要不要从北京搬到成都生活",
        "constraints": ["远程工作", "有孩子要上小学", "北京有一套房"],
        "risk_tolerance": "moderate",
        "seed_history": {
            "query": "要不要搬到郊区住大房子",
            "recommended": {"id": "stay-city", "label": "留在市区"},
            "user_choice": {"id": "stay-city", "label": "留在市区"},
            "user_feedback": 4.0,
            "scores": [
                {"id": "stay-city", "scores": {"quality_of_life": 0.65, "cost_of_living": 0.35, "career_opportunity": 0.9, "social_network": 0.85, "environment": 0.4, "convenience": 0.9}},
                {"id": "move-suburb", "scores": {"quality_of_life": 0.8, "cost_of_living": 0.75, "career_opportunity": 0.5, "social_network": 0.4, "environment": 0.85, "convenience": 0.45}},
            ],
            "weights_used": {"quality_of_life": 0.25, "cost_of_living": 0.2, "career_opportunity": 0.2, "social_network": 0.15, "environment": 0.1, "convenience": 0.1},
        },
        "options": [
            {
                "id": "stay-beijing", "label": "留在北京",
                "dimensions": {"quality_of_life": 0.6, "cost_of_living": 0.3, "career_opportunity": 0.85, "social_network": 0.9, "environment": 0.35, "convenience": 0.8},
                "risks": ["生活成本持续高", "空气质量", "竞争压力大"],
                "opportunities": ["社交圈稳定", "教育资源丰富", "房产保值"],
            },
            {
                "id": "move-chengdu", "label": "搬到成都",
                "dimensions": {"quality_of_life": 0.85, "cost_of_living": 0.75, "career_opportunity": 0.55, "social_network": 0.35, "environment": 0.8, "convenience": 0.7},
                "risks": ["社交圈需要重建", "孩子转学适应", "远程工作时差问题少但出差多"],
                "opportunities": ["生活成本降低", "生活节奏舒适", "美食之都"],
            },
        ],
    },
    "relationship": {
        "query": "朋友邀请合伙创业，要不要加入",
        "constraints": ["目前有稳定工作", "对方技术很强但管理经验少", "需要出资 20 万"],
        "risk_tolerance": "moderate",
        "seed_history": {
            "query": "同事想一起做副业，该不该答应",
            "recommended": {"id": "join-side", "label": "参与副业"},
            "user_choice": {"id": "decline", "label": "婉拒"},
            "user_feedback": 4.3,
            "scores": [
                {"id": "join-side", "scores": {"trust": 0.6, "growth": 0.7, "compatibility": 0.55, "investment": 0.4, "reciprocity": 0.5}},
                {"id": "decline", "scores": {"trust": 0.8, "growth": 0.4, "compatibility": 0.75, "investment": 0.9, "reciprocity": 0.7}},
            ],
            "weights_used": {"trust": 0.25, "growth": 0.2, "compatibility": 0.2, "investment": 0.15, "reciprocity": 0.2},
        },
        "options": [
            {
                "id": "join-startup", "label": "加入合伙创业",
                "dimensions": {"trust": 0.75, "growth": 0.9, "compatibility": 0.65, "investment": 0.3, "reciprocity": 0.6},
                "risks": ["20 万出资有风险", "可能影响友情", "放弃稳定收入"],
                "opportunities": ["高成长可能", "深度合作关系", "自主决策空间"],
            },
            {
                "id": "decline-politely", "label": "婉拒但保持关注",
                "dimensions": {"trust": 0.85, "growth": 0.35, "compatibility": 0.8, "investment": 0.95, "reciprocity": 0.75},
                "risks": ["错过创业机会", "朋友可能失望"],
                "opportunities": ["保持友情", "保留稳定收入", "后续可能再加入"],
            },
            {
                "id": "partial-invest", "label": "不全职加入但投资 10 万做股东",
                "dimensions": {"trust": 0.7, "growth": 0.6, "compatibility": 0.7, "investment": 0.55, "reciprocity": 0.65},
                "risks": ["出资风险", "角色定位模糊"],
                "opportunities": ["保留本职工作", "参与分红", "保持深度参与"],
            },
        ],
    },
}

ALL_DOMAINS = list(DOMAIN_DEMOS.keys())


def _build_context(decision_memory_dir: Path) -> ToolExecutionContext:
    """构造 Demo 运行上下文。"""
    return ToolExecutionContext(
        cwd=Path.cwd(),
        metadata={"decision_memory_dir": str(decision_memory_dir)},
    )


def _seed_domain_history(decision_memory_dir: Path, domain: str) -> None:
    """预置领域历史样本。

    每个领域 4 条历史记录，表达稳定的用户偏好模式，
    以便 demo 能展示个性化权重学习效果。
    """
    config = DOMAIN_DEMOS[domain]
    seed = config["seed_history"]
    memory = DecisionMemory(base_dir=decision_memory_dir)

    for index in range(4):
        record = DecisionRecord(
            decision_id=f"{domain}-seed-{index:03d}",
            user_id="demo-user",
            scenario=domain,
            query=seed["query"],
            user_choice=seed["user_choice"],
            user_feedback=seed["user_feedback"],
            scores=seed["scores"],
            weights_used=seed["weights_used"],
            recommended=seed["recommended"],
            alternatives=[
                opt for opt in [seed.get("user_choice"), seed.get("recommended")]
                if opt and opt["id"] != seed["recommended"]["id"]
            ],
            explanation=f"Demo 预置历史 - {domain} 领域偏好学习样本。",
            created_at=datetime.now(timezone.utc),
        )
        memory.save(record)


async def run_lifegoal_demo(domain: str = "career") -> dict[str, Any]:
    """执行人生目标决策 demo，返回结构化结果。

    Args:
        domain: 决策领域，默认 career。支持全部 6 个领域。
    """
    if domain not in DOMAIN_DEMOS:
        return {"error": f"不支持的领域: {domain}，可选: {', '.join(ALL_DOMAINS)}"}

    config = DOMAIN_DEMOS[domain]

    with TemporaryDirectory(prefix=f"velaris-{domain}-demo-") as temp_dir:
        decision_memory_dir = Path(temp_dir) / "decisions"
        _seed_domain_history(decision_memory_dir, domain)
        context = _build_context(decision_memory_dir)

        # Step 1: 召回偏好
        recall_preferences = await RecallPreferencesTool().execute(
            RecallPreferencesInput(user_id="demo-user", scenario=domain),
            context,
        )

        # Step 2: 召回历史决策
        recall_decisions = await RecallDecisionsTool().execute(
            RecallDecisionsInput(
                user_id="demo-user",
                scenario=domain,
                query=config["query"],
            ),
            context,
        )

        # Step 3: 人生目标决策分析
        lifegoal_result = await LifeGoalTool().execute(
            LifeGoalToolInput(
                domain=domain,
                user_id="demo-user",
                constraints=config["constraints"],
                risk_tolerance=config["risk_tolerance"],
                options=config["options"],
            ),
            context,
        )

        decision_payload = json.loads(lifegoal_result.output)

        # Step 4: 保存决策
        save_result = await SaveDecisionTool().execute(
            SaveDecisionInput(
                user_id="demo-user",
                scenario=domain,
                query=config["query"],
                recommended=decision_payload["recommended"],
                alternatives=decision_payload["alternatives"],
                weights_used=decision_payload["weights_used"],
                explanation=f"Demo 自动保存 {domain} 领域决策结果。",
                options_discovered=decision_payload["all_ranked"],
                tools_called=[
                    "recall_preferences",
                    "recall_decisions",
                    "lifegoal_decide",
                    "save_decision",
                ],
            ),
            context,
        )

        return {
            "领域": domain,
            "问题": config["query"],
            "偏好召回": json.loads(recall_preferences.output),
            "历史决策召回": json.loads(recall_decisions.output),
            "人生目标决策结果": decision_payload,
            "保存结果": json.loads(save_result.output),
        }


def run_lifegoal_demo_sync(domain: str = "career") -> dict[str, Any]:
    """同步方式运行 demo。"""
    return asyncio.run(run_lifegoal_demo(domain))


def render_lifegoal_demo_output(payload: dict[str, Any]) -> str:
    """把 demo 结果渲染成可读文本。"""
    sections: list[str] = []
    for title, value in payload.items():
        if isinstance(value, (dict, list)):
            sections.append(f"=== {title} ===")
            sections.append(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            sections.append(f"=== {title} === {value}")
    return "\n\n".join(sections)


def serialize_lifegoal_demo_output(payload: dict[str, Any]) -> str:
    """把 demo 结果序列化为 JSON 文本。"""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_lifegoal_demo_output(payload: dict[str, Any], path: str | Path) -> Path:
    """把 demo 输出保存到文件。"""
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_lifegoal_demo_output(payload), encoding="utf-8")
    return output_path
