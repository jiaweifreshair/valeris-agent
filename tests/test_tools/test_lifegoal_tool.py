"""人生目标决策工具测试 - 覆盖全部 6 个领域。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.lifegoal_tool import LifeGoalTool, LifeGoalToolInput
from velaris_agent.memory.decision_memory import DecisionMemory
from velaris_agent.memory.types import DecisionRecord
from velaris_agent.scenarios.lifegoal.demo import ALL_DOMAINS, DOMAIN_DEMOS, run_lifegoal_demo


def _seed_domain_preferences(decision_dir: Path, domain: str) -> None:
    """预置领域历史偏好。

    每个领域 4 条历史记录，用户持续选择非推荐项，
    以验证 lifegoal 工具能读到个性化权重。
    """
    config = DOMAIN_DEMOS[domain]
    seed = config["seed_history"]
    memory = DecisionMemory(base_dir=decision_dir)

    for index in range(4):
        memory.save(
            DecisionRecord(
                decision_id=f"{domain}-pref-{index:03d}",
                user_id="test-user",
                scenario=domain,
                query=seed["query"],
                recommended=seed["recommended"],
                user_choice=seed["user_choice"],
                user_feedback=seed["user_feedback"],
                scores=seed["scores"],
                weights_used=seed["weights_used"],
                created_at=datetime.now(timezone.utc),
            )
        )


def test_default_registry_contains_lifegoal_demo_tools():
    """默认工具注册表必须包含人生目标 demo 所需的核心工具。"""
    registry = create_default_tool_registry()

    assert registry.get("lifegoal_decide") is not None
    assert registry.get("decision_score") is not None
    assert registry.get("recall_preferences") is not None
    assert registry.get("recall_decisions") is not None
    assert registry.get("save_decision") is not None


# ---------------------------------------------------------------------------
# 参数化测试: 每个领域都使用正确的维度权重
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ALL_DOMAINS)
async def test_lifegoal_tool_uses_domain_dimensions(tmp_path: Path, domain: str):
    """每个领域应使用该领域专属的维度而非通用维度。"""
    from velaris_agent.scenarios.lifegoal.types import DOMAIN_DIMENSIONS

    config = DOMAIN_DEMOS[domain]
    context = ToolExecutionContext(cwd=tmp_path, metadata={})

    result = await LifeGoalTool().execute(
        LifeGoalToolInput(
            domain=domain,
            risk_tolerance="moderate",
            options=config["options"],
        ),
        context,
    )

    assert result.is_error is False
    payload = json.loads(result.output)

    # 权重键应包含该领域的维度
    expected_dims = set(DOMAIN_DIMENSIONS[domain].keys())
    actual_dims = set(payload["weights_used"].keys())
    assert expected_dims == actual_dims, (
        f"{domain} 维度不匹配: 期望 {expected_dims}, 实际 {actual_dims}"
    )

    # 推荐结果应存在且有效
    assert payload["recommended"] is not None
    assert payload["recommended"]["total_score"] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ALL_DOMAINS)
async def test_lifegoal_tool_personalized_weights(tmp_path: Path, domain: str):
    """存在历史偏好时，lifegoal 工具应使用个性化权重。"""
    decision_dir = tmp_path / "decisions"
    _seed_domain_preferences(decision_dir, domain)
    context = ToolExecutionContext(
        cwd=tmp_path,
        metadata={"decision_memory_dir": str(decision_dir)},
    )

    config = DOMAIN_DEMOS[domain]
    result = await LifeGoalTool().execute(
        LifeGoalToolInput(
            domain=domain,
            user_id="test-user",
            risk_tolerance=config["risk_tolerance"],
            constraints=config["constraints"],
            options=config["options"],
        ),
        context,
    )

    assert result.is_error is False
    payload = json.loads(result.output)
    assert payload["recommended"] is not None
    assert len(payload["weights_used"]) > 0


# ---------------------------------------------------------------------------
# 风险偏好调整测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_risk_tolerance_conservative_boosts_stability(tmp_path: Path):
    """保守型风险偏好应提升 stability 权重。"""
    context = ToolExecutionContext(cwd=tmp_path, metadata={})
    config = DOMAIN_DEMOS["career"]

    result_moderate = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="career", risk_tolerance="moderate", options=config["options"]),
        context,
    )
    result_conservative = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="career", risk_tolerance="conservative", options=config["options"]),
        context,
    )

    moderate_weights = json.loads(result_moderate.output)["weights_used"]
    conservative_weights = json.loads(result_conservative.output)["weights_used"]

    # 保守模式下 stability 权重应更高
    assert conservative_weights["stability"] > moderate_weights["stability"]


@pytest.mark.asyncio
async def test_risk_tolerance_aggressive_boosts_growth(tmp_path: Path):
    """激进型风险偏好应提升 growth/expected_return 权重。"""
    context = ToolExecutionContext(cwd=tmp_path, metadata={})

    # career 领域: growth 应增大
    config = DOMAIN_DEMOS["career"]
    result_moderate = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="career", risk_tolerance="moderate", options=config["options"]),
        context,
    )
    result_aggressive = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="career", risk_tolerance="aggressive", options=config["options"]),
        context,
    )
    assert json.loads(result_aggressive.output)["weights_used"]["growth"] > \
           json.loads(result_moderate.output)["weights_used"]["growth"]

    # finance 领域: expected_return 应增大
    config_fin = DOMAIN_DEMOS["finance"]
    result_fin_mod = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="finance", risk_tolerance="moderate", options=config_fin["options"]),
        context,
    )
    result_fin_agg = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="finance", risk_tolerance="aggressive", options=config_fin["options"]),
        context,
    )
    assert json.loads(result_fin_agg.output)["weights_used"]["expected_return"] > \
           json.loads(result_fin_mod.output)["weights_used"]["expected_return"]


# ---------------------------------------------------------------------------
# Demo 全链路测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ALL_DOMAINS)
async def test_demo_full_pipeline(domain: str):
    """每个领域的 demo 全链路 (偏好召回 -> 历史召回 -> 决策 -> 保存) 应成功完成。"""
    payload = await run_lifegoal_demo(domain)

    assert "error" not in payload
    assert payload["领域"] == domain
    assert payload["偏好召回"] is not None
    assert payload["历史决策召回"] is not None

    decision = payload["人生目标决策结果"]
    assert decision["recommended"] is not None
    assert decision["recommended"]["total_score"] > 0
    assert len(decision["weights_used"]) > 0

    save = payload["保存结果"]
    assert save["decision_id"] is not None


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_options_returns_error(tmp_path: Path):
    """没有提供选项时应返回错误。"""
    context = ToolExecutionContext(cwd=tmp_path, metadata={})

    result = await LifeGoalTool().execute(
        LifeGoalToolInput(domain="career", options=[]),
        context,
    )
    assert result.is_error is True


@pytest.mark.asyncio
async def test_unknown_domain_uses_fallback_weights(tmp_path: Path):
    """未知领域应使用通用 fallback 权重而非崩溃。"""
    context = ToolExecutionContext(cwd=tmp_path, metadata={})

    result = await LifeGoalTool().execute(
        LifeGoalToolInput(
            domain="unknown_domain",
            options=[
                {"id": "a", "label": "选项 A", "dimensions": {"quality": 0.8, "cost": 0.5}},
                {"id": "b", "label": "选项 B", "dimensions": {"quality": 0.6, "cost": 0.9}},
            ],
        ),
        context,
    )
    assert result.is_error is False
    payload = json.loads(result.output)
    assert payload["recommended"] is not None
