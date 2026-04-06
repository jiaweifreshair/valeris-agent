"""Velaris Token 成本数据源 adapter。"""

from __future__ import annotations

from typing import Any

from velaris_agent.adapters.data_sources import StructuredDataSourceLoader


class TokenCostSourceAdapter:
    """Token 成本数据源 adapter。"""

    def __init__(self, loader: StructuredDataSourceLoader | None = None) -> None:
        """初始化 adapter。"""
        self.loader = loader or StructuredDataSourceLoader()

    async def resolve_payload(self, source: dict[str, Any] | None, overrides: dict[str, Any]) -> dict[str, Any]:
        """解析 Token 成本场景负载。"""
        return await self.loader.merge(source, overrides)
