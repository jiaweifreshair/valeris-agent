"""Tool for creating local cron-style jobs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.services.cron import upsert_cron_job
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronCreateToolInput(BaseModel):
    """Arguments for cron job creation."""

    name: str = Field(description="Unique cron job name")
    schedule: str = Field(description="Human-readable schedule expression")
    command: str = Field(description="Shell command to run when triggered")
    cwd: str | None = Field(default=None, description="Optional working directory override")


class CronCreateTool(BaseTool):
    """Create or replace a local cron job."""

    name = "cron_create"
    description = "Create or replace a local cron-style job."
    input_model = CronCreateToolInput

    async def execute(
        self,
        arguments: CronCreateToolInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        upsert_cron_job(
            {
                "name": arguments.name,
                "schedule": arguments.schedule,
                "command": arguments.command,
                "cwd": arguments.cwd or str(context.cwd),
            }
        )
        return ToolResult(output=f"Created cron job {arguments.name}")
