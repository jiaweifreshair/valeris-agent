"""Velaris RobotClaw 数据源与 runtime adapter。"""

from __future__ import annotations

from typing import Any

from velaris_agent.adapters.data_sources import StructuredDataSourceLoader


class RobotClawDispatchAdapter:
    """RobotClaw 调度数据源 adapter。"""

    def __init__(self, loader: StructuredDataSourceLoader | None = None) -> None:
        """初始化 adapter。"""
        self.loader = loader or StructuredDataSourceLoader()

    async def resolve_payload(self, source: dict[str, Any] | None, overrides: dict[str, Any]) -> dict[str, Any]:
        """解析 RobotClaw 场景负载。"""
        return await self.loader.merge(source, overrides)
