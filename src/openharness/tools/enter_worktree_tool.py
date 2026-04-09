"""Tool for creating and entering git worktrees."""

from __future__ import annotations

import subprocess
import re
from pathlib import Path

from pydantic import BaseModel, Field

from openharness.config.paths import get_project_config_dir
from openharness.security import (
    is_protected_write_path,
    render_process_output,
    resolve_security_settings,
    resolve_tool_path,
)
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class EnterWorktreeToolInput(BaseModel):
    """Arguments for entering a worktree."""

    branch: str = Field(description="Target branch name for the worktree")
    path: str | None = Field(default=None, description="Optional worktree path")
    create_branch: bool = Field(default=True)
    base_ref: str = Field(default="HEAD", description="Base ref when creating a new branch")


class EnterWorktreeTool(BaseTool):
    """Create a git worktree."""

    name = "enter_worktree"
    description = "Create a git worktree and return its path."
    input_model = EnterWorktreeToolInput

    async def execute(  # type: ignore[override]
        self,
        arguments: EnterWorktreeToolInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        security_settings = resolve_security_settings(context.metadata.get("security_settings"))
        top_level = _git_output(context.cwd, "rev-parse", "--show-toplevel")
        if top_level is None:
            return ToolResult(output="enter_worktree requires a git repository", is_error=True)

        repo_root = Path(top_level)
        worktree_path = _resolve_worktree_path(repo_root, arguments.branch, arguments.path)
        if is_protected_write_path(worktree_path):
            return ToolResult(
                output=f"Write denied: {worktree_path} 是受保护的系统或凭据路径。",
                is_error=True,
            )
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "worktree", "add"]
        if arguments.create_branch:
            cmd.extend(["-b", arguments.branch, str(worktree_path), arguments.base_ref])
        else:
            cmd.extend([str(worktree_path), arguments.branch])
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = render_process_output(
            stdout=result.stdout,
            stderr=result.stderr,
            redact_secrets=security_settings.redact_secrets,
            default_text=(
                f"Created worktree {worktree_path}"
                if result.returncode == 0
                else f"git worktree add failed for {worktree_path}"
            ),
        )
        if result.returncode != 0:
            return ToolResult(output=output, is_error=True)
        return ToolResult(output=f"{output}\nPath: {worktree_path}")


def _git_output(cwd: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def _resolve_worktree_path(repo_root: Path, branch: str, path: str | None) -> Path:
    if path:
        return resolve_tool_path(repo_root, path)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-") or "worktree"
    return (get_project_config_dir(repo_root) / "worktrees" / slug).resolve()
