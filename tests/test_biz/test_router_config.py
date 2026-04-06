"""Velaris 路由配置驱动测试。"""

from __future__ import annotations

from pathlib import Path

from openharness.biz.engine import build_capability_plan
from openharness.velaris.router import PolicyRouter


def test_router_uses_yaml_policy_for_low_risk_tokencost():
    router = PolicyRouter()
    plan = build_capability_plan(
        query="我每月 OpenAI 成本 2000 美元，想降到 800",
        constraints={"target_monthly_cost": 800},
    )

    decision = router.route(plan=plan, query=plan["query"])

    assert decision.selected_strategy == "local_closed_loop"
    assert decision.selected_route.runtime == "self"
    assert decision.stop_profile == "fast_fail"
    assert decision.trace["selected_rule"] == "R005_simple_local"
    assert "R005_simple_local" in decision.reason_codes


def test_router_uses_yaml_policy_for_audit_required_robotclaw():
    router = PolicyRouter()
    plan = build_capability_plan(
        query="为 robotaxi 派单生成服务提案并形成交易合约",
        constraints={"requires_audit": True},
    )

    decision = router.route(plan=plan, query=plan["query"])

    assert decision.selected_strategy == "delegated_robotclaw"
    assert decision.selected_route.runtime == "robotclaw"
    assert decision.stop_profile == "strict_approval"
    assert decision.trace["selected_rule"] == "R001_high_risk_go_robotclaw"
    assert "R001_high_risk_go_robotclaw" in decision.reason_codes


def test_router_supports_explicit_policy_path_override(tmp_path: Path):
    policy_path = tmp_path / "routing-policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                "version: 1",
                "policy_id: test-routing",
                "defaults:",
                "  strategy: local_closed_loop",
                "  mode: local",
                "  runtime: self",
                "  autonomy: auto",
                "  stop_profile: balanced",
                "stop_profiles:",
                "  balanced:",
                "    description: 默认平衡策略",
                "    on_match: degrade",
                "    conditions:",
                "      - id: runtime_unhealthy",
                "strategies:",
                "  local_closed_loop:",
                "    mode: local",
                "    runtime: self",
                "    autonomy: auto",
                "    max_parallel_workers: 1",
                "    required_capabilities:",
                "      - read",
                "      - reason",
                "rules:",
                "  - id: TEST_ALWAYS_LOCAL",
                "    priority: 1",
                "    when:",
                "      all:",
                "        - field: risk.level",
                "          op: in",
                "          value: [low, medium, high, critical]",
                "    route:",
                "      strategy: local_closed_loop",
                "      stop_profile: balanced",
                "      reason: test-local",
                "fallback:",
                "  strategy: local_closed_loop",
                "  stop_profile: balanced",
                "  reason: fallback-local",
            ]
        ),
        encoding="utf-8",
    )
    router = PolicyRouter(policy_path=policy_path)
    plan = build_capability_plan(
        query="任何任务都本地执行",
        constraints={"requires_audit": True},
        scenario="robotclaw",
    )

    decision = router.route(plan=plan, query=plan["query"])

    assert decision.selected_strategy == "local_closed_loop"
    assert decision.trace["selected_rule"] == "TEST_ALWAYS_LOCAL"
    assert decision.reason_codes[1] == "test-local"
