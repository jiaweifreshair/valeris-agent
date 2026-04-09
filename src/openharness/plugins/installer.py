"""Plugin installation helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from openharness.plugins.loader import get_user_plugins_dir


def install_plugin_from_path(source: str | Path) -> Path:
    """把插件目录安装到用户插件目录。

    这里会把目标路径强制限制在用户插件根目录下，避免未来在路径拼接
    调整时出现“覆盖到根目录外”的回归问题。
    """

    src = Path(source).resolve()
    if not src.exists() or not src.is_dir():
        raise ValueError(f"Plugin source is not a directory: {src}")

    user_root = get_user_plugins_dir().resolve()
    dest = (user_root / src.name).resolve()
    if not _is_relative_to(dest, user_root):
        raise ValueError(f"Plugin install target escapes plugin directory: {dest}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def uninstall_plugin(name: str) -> bool:
    """按目录名卸载用户插件。

    仅接受单段插件目录名，拒绝绝对路径、`..`、分隔符等路径逃逸输入，
    防止 `/plugin uninstall ../../foo` 一类调用删除插件根目录外的内容。
    """

    path = _resolve_user_plugin_path(name)
    if path is None:
        return False
    if not path.exists():
        return False
    shutil.rmtree(path)
    return True


def _resolve_user_plugin_path(name: str) -> Path | None:
    """把插件名解析为用户插件根目录下的安全路径。"""

    raw = name.strip()
    if not raw:
        return None

    candidate = Path(raw)
    if candidate.is_absolute():
        return None
    if len(candidate.parts) != 1:
        return None
    if candidate.name in {"", ".", ".."}:
        return None

    user_root = get_user_plugins_dir().resolve()
    target = (user_root / candidate.name).resolve()
    if not _is_relative_to(target, user_root):
        return None
    return target


def _is_relative_to(path: Path, base: Path) -> bool:
    """兼容 Python 3.10 的相对路径判断。"""

    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False
