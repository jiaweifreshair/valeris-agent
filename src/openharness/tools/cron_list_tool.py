"""Tool for listing local cron jobs."""

from __future__ import annotations

from pydantic import BaseModel

from openharness.services.cron import load_cron_jobs
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronListToolInput(BaseModel):
    """Arguments for cron listing."""


class CronListTool(BaseTool):
    """List local cron jobs."""

    name = "cron_list"
    description = "List configured local cron-style jobs."
    input_model = CronListToolInput

    def is_read_only(self, arguments: CronListToolInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: CronListToolInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del arguments, context
        jobs = load_cron_jobs()
        if not jobs:
            return ToolResult(output="No cron jobs configured.")
        lines = []
        for job in jobs:
            lines.append(f"{job['name']} [{job['schedule']}] -> {job['command']}")
        return ToolResult(output="\n".join(lines))
