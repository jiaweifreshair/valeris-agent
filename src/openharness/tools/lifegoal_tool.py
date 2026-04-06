"""人生目标决策工具 - 分析选项并给出推荐。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class LifeGoalToolInput(BaseModel):
    """人生目标决策工具输入。"""

    domain: str = Field(
        description="决策领域: career/finance/health/education/lifestyle/relationship"
    )
    options: list[dict[str, Any]] = Field(
        default_factory=list,
        description="候选选项列表, 每项含 id, label, dimensions (评分字典)"
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="约束条件, 如 ['有房贷', '孩子明年上学']"
    )
    risk_tolerance: str = Field(
        default="moderate",
        description="风险偏好: conservative/moderate/aggressive"
    )
    user_id: str = Field(
        default="",
        description="用户 ID (用于个性化权重, 可选)"
    )


class LifeGoalTool(BaseTool):
    """人生目标决策工具。

    分析用户提供的人生选项, 基于多维评分和个性化权重给出推荐。
    支持职业/财务/健康/教育/生活/关系六大领域。
    """

    name = "lifegoal_decide"
    description = (
        "分析人生重大决策的选项并给出推荐. "
        "支持六大领域: 职业(career), 财务(finance), 健康(health), "
        "教育(education), 生活(lifestyle), 关系(relationship). "
        "输入选项列表和约束条件, 返回带评分和理由的推荐."
    )
    input_model = LifeGoalToolInput

    async def execute(
        self, arguments: LifeGoalToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        """执行人生目标决策分析。"""
        try:
            from velaris_agent.scenarios.lifegoal.types import DOMAIN_DIMENSIONS

            domain = arguments.domain
            options = arguments.options
            risk_tolerance = arguments.risk_tolerance

            if not options:
                return ToolResult(
                    output="没有提供候选选项, 请先描述你面临的选择.",
                    is_error=True,
                )

            # 获取领域默认权重
            weights = dict(DOMAIN_DIMENSIONS.get(domain, {
                "quality": 0.4, "cost": 0.3, "risk": 0.3
            }))

            # 风险偏好调整
            if risk_tolerance == "conservative":
                for dim in weights:
                    if dim in ("risk", "stability"):
                        weights[dim] *= 1.3
            elif risk_tolerance == "aggressive":
                for dim in weights:
                    if dim in ("growth", "expected_return", "career_impact"):
                        weights[dim] *= 1.3

            # 尝试个性化权重
            if arguments.user_id:
                try:
                    from velaris_agent.memory.decision_memory import DecisionMemory
                    from velaris_agent.memory.preference_learner import PreferenceLearner

                    memory_dir = context.metadata.get("decision_memory_dir")
                    memory = DecisionMemory(base_dir=memory_dir)
                    learner = PreferenceLearner(memory)
                    prefs = learner.compute_preferences(arguments.user_id, domain)
                    if prefs.confidence > 0.1 and prefs.weights:
                        weights = prefs.weights
                except Exception:
                    pass  # 回退到默认权重

            # 归一化权重
            total_w = sum(max(v, 0.01) for v in weights.values())
            weights = {k: max(v, 0.01) / total_w for k, v in weights.items()}

            # 评分
            scored: list[dict[str, Any]] = []
            for opt in options:
                dims = opt.get("dimensions", {})
                total_score = 0.0
                breakdown: dict[str, float] = {}
                for dim, w in weights.items():
                    val = min(1.0, max(0.0, float(dims.get(dim, 0.5))))
                    breakdown[dim] = round(val, 3)
                    total_score += val * w

                scored.append({
                    "id": opt.get("id", ""),
                    "label": opt.get("label", ""),
                    "total_score": round(total_score, 4),
                    "breakdown": breakdown,
                    "risks": opt.get("risks", []),
                    "opportunities": opt.get("opportunities", []),
                })

            scored.sort(key=lambda x: x["total_score"], reverse=True)

            # 约束过滤标注
            for item in scored:
                item["constraints_satisfied"] = True  # 简化: 约束由 Agent 推理判断

            result = {
                "domain": domain,
                "risk_tolerance": risk_tolerance,
                "weights_used": {k: round(v, 4) for k, v in weights.items()},
                "recommended": scored[0] if scored else None,
                "alternatives": scored[1:3] if len(scored) > 1 else [],
                "all_ranked": scored,
                "constraints": arguments.constraints,
                "action_hint": (
                    "建议用 save_decision 记录本次决策, "
                    "一段时间后用 recall_decisions 回顾结果."
                ),
            }

            return ToolResult(
                output=json.dumps(result, ensure_ascii=False, indent=2)
            )

        except Exception as exc:
            return ToolResult(output=f"决策分析失败: {exc}", is_error=True)

    def is_read_only(self, arguments: LifeGoalToolInput) -> bool:
        """只读工具。"""
        return True
