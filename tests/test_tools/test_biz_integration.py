"""Integration tests for Velaris business flows across the default registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


@pytest.mark.asyncio
async def test_biz_travel_flow_across_registry(tmp_path: Path):
    registry = create_default_tool_registry()
    context = ToolExecutionContext(cwd=tmp_path, metadata={"tool_registry": registry})

    biz_plan = registry.get("biz_plan")
    biz_run = registry.get("biz_run_scenario")

    plan_result = await biz_plan.execute(
        biz_plan.input_model(
            query="下周去上海出差，帮我做商旅推荐",
            constraints={"budget_max": 3000, "direct_only": True},
        ),
        context,
    )
    plan = json.loads(plan_result.output)
    assert plan["scenario"] == "travel"

    run_result = await biz_run.execute(
        biz_run.input_model(
            scenario=plan["scenario"],
            payload={
                "budget_max": 3000,
                "direct_only": True,
                "options": [
                    {
                        "id": "travel-a",
                        "label": "直飞方案",
                        "price": 1500,
                        "duration_minutes": 150,
                        "comfort": 0.78,
                        "direct": True,
                    },
                    {
                        "id": "travel-b",
                        "label": "转机方案",
                        "price": 1100,
                        "duration_minutes": 350,
                        "comfort": 0.52,
                        "direct": False,
                    },
                ],
            },
        ),
        context,
    )
    payload = json.loads(run_result.output)
    assert payload["recommended"]["id"] == "travel-a"


@pytest.mark.asyncio
async def test_biz_tokencost_flow_across_registry(tmp_path: Path):
    registry = create_default_tool_registry()
    context = ToolExecutionContext(cwd=tmp_path, metadata={"tool_registry": registry})

    biz_plan = registry.get("biz_plan")
    biz_run = registry.get("biz_run_scenario")

    plan_result = await biz_plan.execute(
        biz_plan.input_model(
            query="我每月 OpenAI 成本 2000 美元，想降到 800",
            constraints={"target_monthly_cost": 800},
        ),
        context,
    )
    plan = json.loads(plan_result.output)
    assert plan["scenario"] == "tokencost"

    run_result = await biz_run.execute(
        biz_run.input_model(
            scenario=plan["scenario"],
            payload={
                "current_monthly_cost": 2000,
                "target_monthly_cost": 800,
                "suggestions": [
                    {
                        "id": "switch-tier",
                        "title": "分层路由",
                        "estimated_saving": 900,
                        "quality_retention": 0.88,
                        "execution_speed": 0.9,
                        "effort": "medium",
                    },
                    {
                        "id": "cache-enable",
                        "title": "缓存命中",
                        "estimated_saving": 250,
                        "quality_retention": 0.97,
                        "execution_speed": 0.75,
                        "effort": "low",
                    },
                ],
            },
        ),
        context,
    )
    payload = json.loads(run_result.output)
    assert payload["recommendations"][0]["id"] == "switch-tier"
    assert payload["projected_monthly_cost"] == 850


@pytest.mark.asyncio
async def test_biz_openclaw_flow_across_registry(tmp_path: Path):
    registry = create_default_tool_registry()
    context = ToolExecutionContext(cwd=tmp_path, metadata={"tool_registry": registry})

    biz_plan = registry.get("biz_plan")
    biz_run = registry.get("biz_run_scenario")

    plan_result = await biz_plan.execute(
        biz_plan.input_model(
            query="为 robotaxi 派单生成服务提案并形成交易合约",
            constraints={"requires_audit": True},
        ),
        context,
    )
    plan = json.loads(plan_result.output)
    assert plan["scenario"] == "openclaw"
    assert plan["governance"]["requires_audit"] is True

    run_result = await biz_run.execute(
        biz_run.input_model(
            scenario=plan["scenario"],
            payload={
                "max_budget_cny": 200000,
                "proposals": [
                    {
                        "id": "dispatch-a",
                        "price_cny": 180000,
                        "eta_minutes": 22,
                        "safety_score": 0.95,
                        "compliance_score": 0.95,
                        "available": True,
                    },
                    {
                        "id": "dispatch-b",
                        "price_cny": 100000,
                        "eta_minutes": 18,
                        "safety_score": 0.68,
                        "compliance_score": 0.82,
                        "available": True,
                    },
                ],
            },
        ),
        context,
    )
    payload = json.loads(run_result.output)
    assert payload["recommended"]["id"] == "dispatch-a"
