"""Tests for Velaris business capability engine."""

from __future__ import annotations

from openharness.biz.engine import build_capability_plan, run_scenario, score_options


def test_build_capability_plan_for_travel_query():
    plan = build_capability_plan(
        query="下周去上海出差，帮我做机票酒店组合推荐，预算 3000",
        constraints={"budget_max": 3000, "direct_only": True},
    )

    assert plan["scenario"] == "travel"
    assert "intent_parse" in plan["capabilities"]
    assert plan["governance"]["requires_audit"] is False
    assert plan["decision_weights"]["price"] > 0


def test_score_options_returns_ranked_results():
    ranked = score_options(
        options=[
            {
                "id": "balanced",
                "label": "Balanced",
                "scores": {"quality": 0.8, "cost": 0.7, "speed": 0.6},
            },
            {
                "id": "cheap",
                "label": "Cheap",
                "scores": {"quality": 0.5, "cost": 0.95, "speed": 0.7},
            },
        ],
        weights={"quality": 0.35, "cost": 0.5, "speed": 0.15},
    )

    assert ranked[0]["id"] == "cheap"
    assert ranked[0]["total_score"] >= ranked[1]["total_score"]


def test_run_tokencost_scenario_returns_projected_cost():
    result = run_scenario(
        scenario="tokencost",
        payload={
            "current_monthly_cost": 2000,
            "target_monthly_cost": 800,
            "suggestions": [
                {
                    "id": "switch-mini",
                    "title": "切换到 mini 模型",
                    "estimated_saving": 700,
                    "quality_retention": 0.9,
                    "execution_speed": 0.9,
                    "effort": "low",
                },
                {
                    "id": "prompt-compress",
                    "title": "压缩 Prompt",
                    "estimated_saving": 300,
                    "quality_retention": 0.95,
                    "execution_speed": 0.8,
                    "effort": "low",
                },
            ],
        },
    )

    assert result["scenario"] == "tokencost"
    assert result["projected_monthly_cost"] == 1000
    assert result["feasible"] is False
    assert result["recommendations"][0]["id"] == "switch-mini"


def test_run_robotclaw_scenario_prefers_safe_compliant_option():
    result = run_scenario(
        scenario="robotclaw",
        payload={
            "max_budget_cny": 200000,
            "proposals": [
                {
                    "id": "proposal-a",
                    "price_cny": 160000,
                    "eta_minutes": 28,
                    "safety_score": 0.92,
                    "compliance_score": 0.96,
                    "available": True,
                },
                {
                    "id": "proposal-b",
                    "price_cny": 120000,
                    "eta_minutes": 24,
                    "safety_score": 0.7,
                    "compliance_score": 0.8,
                    "available": True,
                },
            ],
        },
    )

    assert result["scenario"] == "robotclaw"
    assert result["recommended"]["id"] == "proposal-a"
    assert result["contract_ready"] is True
