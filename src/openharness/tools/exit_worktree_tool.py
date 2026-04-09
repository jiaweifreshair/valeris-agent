"""Tool for removing git worktrees."""

from __future__ import annotations

import subprocess

from pydantic import BaseModel, Field

from openharness.security import (
    is_protected_write_path,
    render_process_output,
    resolve_security_settings,
    resolve_tool_path,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class ExitWorktreeToolInput(BaseModel):
    """Arguments for worktree removal."""

    path: str = Field(description="Worktree path to remove")


class ExitWorktreeTool(BaseTool):
    """Remove a git worktree."""

    name = "exit_worktree"
    description = "Remove a git worktree by path."
    input_model = ExitWorktreeToolInput

    async def execute(  # type: ignore[override]
        self,
        arguments: ExitWorktreeToolInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        security_settings = resolve_security_settings(context.metadata.get("security_settings"))
        path = resolve_tool_path(context.cwd, arguments.path)
        if is_protected_write_path(path):
            return ToolResult(
                output=f"Write denied: {path} 是受保护的系统或凭据路径。",
                is_error=True,
            )
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", str(path)],
            cwd=context.cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        output = render_process_output(
            stdout=result.stdout,
            stderr=result.stderr,
            redact_secrets=security_settings.redact_secrets,
            default_text=(
                f"Removed worktree {path}"
                if result.returncode == 0
                else f"git worktree remove failed for {path}"
            ),
        )
        return ToolResult(output=output, is_error=result.returncode != 0)
