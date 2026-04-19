"""execution 召回工具测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext


@pytest.mark.asyncio
async def test_biz_recall_execution_tool_roundtrips_latest_execution(tmp_path: Path) -> None:
    """biz_execute 产生的 execution 必须可被 biz_recall_execution 召回。"""

    registry = create_default_tool_registry()
    context = ToolExecutionContext(
        cwd=tmp_path,
        metadata={
            "tool_registry": registry,
        },
    )

    biz_execute = registry.get("biz_execute")
    assert biz_execute is not None

    created = await biz_execute.execute(
        biz_execute.input_model(
            query="我每月 AI API 花费很高，帮我做降本分析",
            constraints={"target_monthly_cost": 800},
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
                    }
                ],
            },
        ),
        context,
    )
    assert created.is_error is False
    created_payload = json.loads(created.output)
    execution_id = created_payload["envelope"]["execution"]["execution_id"]

    recall_tool = registry.get("biz_recall_execution")
    assert recall_tool is not None

    recalled = await recall_tool.execute(
        recall_tool.input_model(execution_id=execution_id),
        context,
    )
    assert recalled.is_error is False
    recalled_payload = json.loads(recalled.output)
    assert recalled_payload["envelope"]["execution"]["execution_id"] == execution_id
    assert recalled_payload["envelope"]["plan"]["scenario"] == "tokencost"


@pytest.mark.asyncio
async def test_biz_list_executions_tool_includes_latest_execution(tmp_path: Path) -> None:
    registry = create_default_tool_registry()
    context = ToolExecutionContext(
        cwd=tmp_path,
        metadata={
            "tool_registry": registry,
        },
    )

    biz_execute = registry.get("biz_execute")
    assert biz_execute is not None

    created = await biz_execute.execute(
        biz_execute.input_model(
            query="我每月 AI API 花费很高，帮我做降本分析",
            constraints={"target_monthly_cost": 800},
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
                    }
                ],
            },
        ),
        context,
    )
    created_payload = json.loads(created.output)
    execution_id = created_payload["envelope"]["execution"]["execution_id"]

    list_tool = registry.get("biz_list_executions")
    assert list_tool is not None

    listed = await list_tool.execute(
        list_tool.input_model(limit=10),
        context,
    )
    assert listed.is_error is False
    listed_payload = json.loads(listed.output)
    assert listed_payload["total"] >= 1
    assert any(item.get("execution_id") == execution_id for item in listed_payload["executions"])

