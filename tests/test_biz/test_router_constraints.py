"""Velaris 显式约束驱动路由测试。"""

from __future__ import annotations

from velaris_agent.biz.engine import build_capability_plan
from velaris_agent.velaris.router import PolicyRouter


def test_router_prefers_explicit_code_constraints_for_tokencost():
    router = PolicyRouter()
    plan = build_capability_plan(
        query="分析我当前模型调用成本并输出改造方案",
        constraints={
            "target_monthly_cost": 800,
            "write_code": True,
            "task_complexity": "complex",
            "external_side_effects": False,
            "risk_level": "medium",
        },
        scenario="tokencost",
    )

    decision = router.route(plan=plan, query=plan["query"])

    assert decision.selected_strategy == "delegated_claude_code"
    assert decision.trace["selected_rule"] == "R002_code_heavy_go_claude_code"


def test_router_prefers_explicit_cross_system_constraints_for_travel():
    router = PolicyRouter()
    plan = build_capability_plan(
        query="生成商旅建议并同步改写公司差旅工作流代码",
        constraints={
            "write_code": True,
            "external_side_effects": True,
            "risk_level": "medium",
            "task_complexity": "complex",
        },
        scenario="travel",
    )

    decision = router.route(plan=plan, query=plan["query"])

    assert decision.selected_strategy == "hybrid_robotclaw_claudecode"
    assert decision.trace["selected_rule"] == "R004_cross_system_use_hybrid"
