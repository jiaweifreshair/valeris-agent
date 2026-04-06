"""Velaris 原生业务能力引擎。

实现三类共享能力：
1. 业务场景识别与能力规划。
2. 多维评分与排序。
3. travel / tokencost / robotclaw 三类场景执行。
"""

from __future__ import annotations

from typing import Any


_SCENARIO_KEYWORDS: dict[str, tuple[str, ...]] = {
    "lifegoal": (
        "lifegoal", "career", "job", "offer", "跳槽", "转行", "创业", "升学",
        "投资", "买房", "理财", "保险", "健康", "运动", "留学", "考证",
        "人生", "决策", "选择", "纠结", "该不该", "怎么选",
    ),
    "travel": ("travel", "flight", "hotel", "trip", "商旅", "出差", "机票", "酒店"),
    "tokencost": ("tokencost", "token", "openai", "anthropic", "模型成本", "降本", "api 花费", "成本优化"),
    "robotclaw": ("robotclaw", "dispatch", "robotaxi", "vehicle", "proposal", "派单", "运力", "合约", "车端"),
}

_SCENARIO_CAPABILITIES: dict[str, list[str]] = {
    "lifegoal": ["intent_parse", "option_discovery", "multi_dim_score", "recommendation", "memory_recall"],
    "travel": ["intent_parse", "inventory_search", "option_score", "itinerary_recommend"],
    "tokencost": ["usage_analyze", "model_compare", "saving_estimate", "optimization_recommend"],
    "robotclaw": ["intent_order", "vehicle_match", "proposal_score", "contract_form"],
}

_SCENARIO_WEIGHTS: dict[str, dict[str, float]] = {
    "lifegoal": {"growth": 0.25, "income": 0.25, "fulfillment": 0.20, "stability": 0.15, "balance": 0.15},
    "travel": {"price": 0.4, "time": 0.35, "comfort": 0.25},
    "tokencost": {"cost": 0.5, "quality": 0.35, "speed": 0.15},
    "robotclaw": {"safety": 0.4, "eta": 0.25, "cost": 0.2, "compliance": 0.15},
}

_SCENARIO_GOVERNANCE: dict[str, dict[str, Any]] = {
    "lifegoal": {
        "requires_audit": False,
        "approval_mode": "default",
        "stop_profile": "balanced",
    },
    "travel": {
        "requires_audit": False,
        "approval_mode": "default",
        "stop_profile": "balanced",
    },
    "tokencost": {
        "requires_audit": False,
        "approval_mode": "default",
        "stop_profile": "balanced",
    },
    "robotclaw": {
        "requires_audit": True,
        "approval_mode": "strict",
        "stop_profile": "strict_approval",
    },
}

_SCENARIO_RECOMMENDED_TOOLS: dict[str, list[str]] = {
    "lifegoal": [
        "lifegoal_decide", "recall_preferences", "recall_decisions",
        "save_decision", "decision_score", "biz_execute",
    ],
    "travel": ["biz_execute", "travel_recommend", "biz_plan", "biz_score"],
    "tokencost": ["biz_execute", "tokencost_analyze", "biz_plan", "biz_score"],
    "robotclaw": ["biz_execute", "robotclaw_dispatch", "biz_plan", "biz_score"],
    "general": ["biz_execute", "biz_plan", "biz_score", "biz_run_scenario"],
}

_OPENCLAW_MIN_SAFETY = 0.9
_OPENCLAW_MIN_COMPLIANCE = 0.9


def infer_scenario(query: str, scenario: str | None = None) -> str:
    """识别业务场景。"""
    if scenario in _SCENARIO_CAPABILITIES:
        return scenario

    lowered = query.lower()
    for candidate, keywords in _SCENARIO_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return candidate
    return "general"


def build_capability_plan(
    query: str,
    constraints: dict[str, Any] | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    """生成业务能力规划。"""
    normalized_constraints = constraints or {}
    resolved_scenario = infer_scenario(query, scenario)
    capabilities = _SCENARIO_CAPABILITIES.get(resolved_scenario, ["generic_analysis", "option_score"])
    governance = dict(
        _SCENARIO_GOVERNANCE.get(
            resolved_scenario,
            {
                "requires_audit": False,
                "approval_mode": "default",
                "stop_profile": "balanced",
            },
        )
    )
    if "requires_audit" in normalized_constraints:
        governance["requires_audit"] = bool(normalized_constraints["requires_audit"])

    decision_weights = dict(_SCENARIO_WEIGHTS.get(resolved_scenario, {"quality": 0.5, "cost": 0.3, "speed": 0.2}))
    return {
        "scenario": resolved_scenario,
        "query": query,
        "constraints": normalized_constraints,
        "capabilities": capabilities,
        "decision_weights": decision_weights,
        "governance": governance,
        "recommended_tools": _SCENARIO_RECOMMENDED_TOOLS.get(
            resolved_scenario,
            _SCENARIO_RECOMMENDED_TOOLS["general"],
        ),
    }


def score_options(options: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
    """对候选项进行多维评分。"""
    total_weight = sum(max(weight, 0.0) for weight in weights.values())
    normalized_weights = {
        dimension: (max(weight, 0.0) / total_weight if total_weight > 0 else 0.0)
        for dimension, weight in weights.items()
    }

    ranked: list[dict[str, Any]] = []
    for option in options:
        raw_scores = option.get("scores", {})
        total_score = 0.0
        normalized_scores: dict[str, float] = {}
        for dimension, weight in normalized_weights.items():
            score = _clamp_score(raw_scores.get(dimension, 0.0))
            normalized_scores[dimension] = score
            total_score += score * weight
        ranked.append(
            {
                "id": option.get("id", ""),
                "label": option.get("label", option.get("id", "")),
                "scores": normalized_scores,
                "total_score": round(total_score, 4),
            }
        )

    return sorted(ranked, key=lambda item: item["total_score"], reverse=True)


def run_scenario(scenario: str, payload: dict[str, Any]) -> dict[str, Any]:
    """运行一个业务场景。"""
    if scenario == "lifegoal":
        return _run_lifegoal_scenario(payload)
    if scenario == "travel":
        return _run_travel_scenario(payload)
    if scenario == "tokencost":
        return _run_tokencost_scenario(payload)
    if scenario == "robotclaw":
        return _run_robotclaw_scenario(payload)
    raise ValueError(f"Unsupported biz scenario: {scenario}")


def _run_travel_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    budget_max = float(payload.get("budget_max", 0) or 0)
    direct_only = bool(payload.get("direct_only", False))
    raw_options = payload.get("options", [])

    eligible_options = [
        option for option in raw_options
        if (budget_max <= 0 or float(option.get("price", 0)) <= budget_max)
        and (not direct_only or bool(option.get("direct", False)))
    ]
    if not eligible_options:
        return {
            "scenario": "travel",
            "recommended": None,
            "cheapest": None,
            "accepted_option_ids": [],
            "summary": "没有满足预算和直飞约束的商旅方案。",
        }

    prices = [float(option.get("price", 0)) for option in eligible_options]
    durations = [float(option.get("duration_minutes", 0)) for option in eligible_options]

    scored_input: list[dict[str, Any]] = []
    for option in eligible_options:
        scored_input.append(
            {
                "id": option.get("id", ""),
                "label": option.get("label", option.get("id", "")),
                "scores": {
                    "price": _inverse_score(float(option.get("price", 0)), prices),
                    "time": _inverse_score(float(option.get("duration_minutes", 0)), durations),
                    "comfort": _clamp_score(float(option.get("comfort", 0))),
                },
            }
        )

    ranked = score_options(scored_input, _SCENARIO_WEIGHTS["travel"])
    cheapest = min(eligible_options, key=lambda option: float(option.get("price", 0)))
    return {
        "scenario": "travel",
        "recommended": ranked[0],
        "cheapest": {
            "id": cheapest.get("id", ""),
            "price": float(cheapest.get("price", 0)),
            "label": cheapest.get("label", cheapest.get("id", "")),
        },
        "accepted_option_ids": [option.get("id", "") for option in eligible_options],
        "summary": f"共筛选出 {len(eligible_options)} 个满足约束的商旅方案。",
    }


def _run_tokencost_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    current_monthly_cost = float(payload.get("current_monthly_cost", 0))
    target_monthly_cost = float(payload.get("target_monthly_cost", 0))
    raw_suggestions = payload.get("suggestions", [])
    effort_scores = {"low": 1.0, "medium": 0.75, "high": 0.5}

    savings = [float(item.get("estimated_saving", 0)) for item in raw_suggestions]
    max_saving = max(savings) if savings else 0.0

    scored_input: list[dict[str, Any]] = []
    for item in raw_suggestions:
        scored_input.append(
            {
                "id": item.get("id", ""),
                "label": item.get("title", item.get("id", "")),
                "scores": {
                    "cost": (float(item.get("estimated_saving", 0)) / max_saving) if max_saving > 0 else 0.0,
                    "quality": _clamp_score(float(item.get("quality_retention", 0))),
                    "speed": _clamp_score(
                        (float(item.get("execution_speed", 0)) + effort_scores.get(str(item.get("effort", "medium")), 0.75)) / 2
                    ),
                },
            }
        )

    recommendations = score_options(scored_input, _SCENARIO_WEIGHTS["tokencost"])
    total_estimated_saving = round(sum(savings), 2)
    projected_monthly_cost = round(max(0.0, current_monthly_cost - total_estimated_saving), 2)
    return {
        "scenario": "tokencost",
        "recommendations": recommendations,
        "total_estimated_saving": total_estimated_saving,
        "projected_monthly_cost": projected_monthly_cost,
        "feasible": projected_monthly_cost <= target_monthly_cost if target_monthly_cost > 0 else True,
        "summary": f"预计月度节省 {total_estimated_saving:.0f}，目标成本 {target_monthly_cost:.0f}。",
    }


def _run_robotclaw_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    max_budget_cny = float(payload.get("max_budget_cny", 0) or 0)
    raw_proposals = payload.get("proposals", [])
    eligible = [
        item for item in raw_proposals
        if bool(item.get("available", False))
        and (max_budget_cny <= 0 or float(item.get("price_cny", 0)) <= max_budget_cny)
    ]
    if not eligible:
        return {
            "scenario": "robotclaw",
            "recommended": None,
            "contract_ready": False,
            "accepted_option_ids": [],
            "summary": "没有满足预算和可用性要求的调度提案。",
        }

    compliant_candidates = [
        item for item in eligible
        if float(item.get("safety_score", 0)) >= _OPENCLAW_MIN_SAFETY
        and float(item.get("compliance_score", 0)) >= _OPENCLAW_MIN_COMPLIANCE
    ]
    ranked_candidates = compliant_candidates or eligible

    prices = [float(item.get("price_cny", 0)) for item in ranked_candidates]
    etas = [float(item.get("eta_minutes", 0)) for item in ranked_candidates]
    scored_input: list[dict[str, Any]] = []
    for item in ranked_candidates:
        scored_input.append(
            {
                "id": item.get("id", ""),
                "label": item.get("label", item.get("id", "")),
                "scores": {
                    "safety": _clamp_score(float(item.get("safety_score", 0))),
                    "eta": _inverse_score(float(item.get("eta_minutes", 0)), etas),
                    "cost": _inverse_score(float(item.get("price_cny", 0)), prices),
                    "compliance": _clamp_score(float(item.get("compliance_score", 0))),
                },
            }
        )

    ranked = score_options(scored_input, _SCENARIO_WEIGHTS["robotclaw"])
    top_id = ranked[0]["id"]
    top_source = next(item for item in ranked_candidates if item.get("id", "") == top_id)
    return {
        "scenario": "robotclaw",
        "recommended": ranked[0],
        "accepted_option_ids": [item.get("id", "") for item in ranked_candidates],
        "contract_ready": (
            float(top_source.get("safety_score", 0)) >= 0.9
            and float(top_source.get("compliance_score", 0)) >= 0.9
        ),
        "summary": (
            f"共评估 {len(eligible)} 个可用提案，"
            f"其中 {len(ranked_candidates)} 个通过安全与合规门槛。"
        ),
    }


def _run_lifegoal_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    """人生目标决策场景。"""
    domain = str(payload.get("domain", "career"))
    raw_options = payload.get("options", [])
    risk_tolerance = str(payload.get("risk_tolerance", "moderate"))
    constraints = payload.get("constraints", [])

    if not raw_options:
        return {
            "scenario": "lifegoal",
            "domain": domain,
            "recommended": None,
            "alternatives": [],
            "summary": "没有提供候选选项, 请描述你面临的选择.",
        }

    # 获取领域权重
    weights = dict(_SCENARIO_WEIGHTS.get("lifegoal", {"quality": 0.5, "cost": 0.3, "risk": 0.2}))

    # 风险偏好调整
    if risk_tolerance == "conservative":
        if "stability" in weights:
            weights["stability"] *= 1.3
    elif risk_tolerance == "aggressive":
        if "growth" in weights:
            weights["growth"] *= 1.3

    scored_input: list[dict[str, Any]] = []
    for opt in raw_options:
        dims = opt.get("dimensions", opt.get("scores", {}))
        scored_input.append({
            "id": opt.get("id", ""),
            "label": opt.get("label", opt.get("id", "")),
            "scores": {k: _clamp_score(float(v)) for k, v in dims.items()},
        })

    ranked = score_options(scored_input, weights)
    return {
        "scenario": "lifegoal",
        "domain": domain,
        "risk_tolerance": risk_tolerance,
        "recommended": ranked[0] if ranked else None,
        "alternatives": ranked[1:3] if len(ranked) > 1 else [],
        "all_ranked": ranked,
        "constraints": constraints,
        "summary": f"在 {domain} 领域分析了 {len(ranked)} 个选项.",
    }


def _inverse_score(value: float, samples: list[float]) -> float:
    if not samples:
        return 0.0
    minimum = min(samples)
    maximum = max(samples)
    if maximum == minimum:
        return 1.0
    return _clamp_score((maximum - value) / (maximum - minimum))


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
