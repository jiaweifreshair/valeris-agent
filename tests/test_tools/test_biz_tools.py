"""Tests for Velaris business tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools.base import ToolExecutionContext
from openharness.tools.biz_plan_tool import BizPlanTool, BizPlanToolInput
from openharness.tools.biz_run_scenario_tool import BizRunScenarioTool, BizRunScenarioToolInput
from openharness.tools.biz_score_tool import BizScoreTool, BizScoreToolInput


@pytest.mark.asyncio
async def test_biz_plan_tool_returns_plan_json(tmp_path: Path):
    result = await BizPlanTool().execute(
        BizPlanToolInput(
            query="我每月 AI API 花费很高，帮我做降本分析",
            constraints={"target_monthly_cost": 800},
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    payload = json.loads(result.output)
    assert result.is_error is False
    assert payload["scenario"] == "tokencost"
    assert "usage_analyze" in payload["capabilities"]
    assert payload["recommended_tools"][0] == "biz_execute"


@pytest.mark.asyncio
async def test_biz_score_tool_returns_ranked_json(tmp_path: Path):
    result = await BizScoreTool().execute(
        BizScoreToolInput(
            options=[
                {"id": "a", "label": "A", "scores": {"quality": 0.7, "cost": 0.7}},
                {"id": "b", "label": "B", "scores": {"quality": 0.6, "cost": 0.95}},
            ],
            weights={"quality": 0.3, "cost": 0.7},
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    ranked = json.loads(result.output)
    assert ranked[0]["id"] == "b"


@pytest.mark.asyncio
async def test_biz_run_scenario_tool_returns_travel_recommendation(tmp_path: Path):
    result = await BizRunScenarioTool().execute(
        BizRunScenarioToolInput(
            scenario="travel",
            payload={
                "budget_max": 3000,
                "direct_only": True,
                "options": [
                    {
                        "id": "plan-1",
                        "label": "早班直飞 + 全季",
                        "price": 1280,
                        "duration_minutes": 160,
                        "comfort": 0.75,
                        "direct": True,
                    },
                    {
                        "id": "plan-2",
                        "label": "转机低价 + 经济酒店",
                        "price": 980,
                        "duration_minutes": 320,
                        "comfort": 0.45,
                        "direct": False,
                    },
                ],
            },
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    payload = json.loads(result.output)
    assert payload["scenario"] == "travel"
    assert payload["recommended"]["id"] == "plan-1"
