"""Velaris 领域业务工具测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools.openclaw_dispatch_tool import OpenClawDispatchTool, OpenClawDispatchToolInput
from openharness.tools.tokencost_analyze_tool import TokenCostAnalyzeTool, TokenCostAnalyzeToolInput
from openharness.tools.travel_recommend_tool import TravelRecommendTool, TravelRecommendToolInput
from openharness.tools.base import ToolExecutionContext


@pytest.mark.asyncio
async def test_travel_recommend_tool_returns_ranked_plan(tmp_path: Path):
    result = await TravelRecommendTool().execute(
        TravelRecommendToolInput(
            budget_max=3000,
            direct_only=True,
            options=[
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
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    payload = json.loads(result.output)
    assert payload["scenario"] == "travel"
    assert payload["recommended"]["id"] == "travel-a"


@pytest.mark.asyncio
async def test_tokencost_analyze_tool_returns_projection(tmp_path: Path):
    result = await TokenCostAnalyzeTool().execute(
        TokenCostAnalyzeToolInput(
            current_monthly_cost=2000,
            target_monthly_cost=800,
            suggestions=[
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
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    payload = json.loads(result.output)
    assert payload["scenario"] == "tokencost"
    assert payload["recommendations"][0]["id"] == "switch-tier"
    assert payload["projected_monthly_cost"] == 850


@pytest.mark.asyncio
async def test_openclaw_dispatch_tool_applies_safety_gate(tmp_path: Path):
    result = await OpenClawDispatchTool().execute(
        OpenClawDispatchToolInput(
            max_budget_cny=200000,
            proposals=[
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
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    payload = json.loads(result.output)
    assert payload["scenario"] == "openclaw"
    assert payload["recommended"]["id"] == "dispatch-a"
    assert payload["contract_ready"] is True
