"""Provider 解析相关测试。"""

from __future__ import annotations

import json
from pathlib import Path

from openharness.api.provider import auth_status, detect_provider, resolve_auth_status
from openharness.config.settings import Settings


def test_detect_provider_prefers_explicit_provider() -> None:
    """显式 provider 应优先于模型名和 base_url 推断。"""

    info = detect_provider(
        Settings(
            provider="moonshot",
            api_format="openai_compat",
            model="claude-sonnet-4-20250514",
        )
    )
    assert info.name == "moonshot"
    assert info.display_name == "Moonshot"


def test_auth_status_uses_provider_specific_env(monkeypatch) -> None:
    """认证状态应识别 provider 对应的环境变量。"""

    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    status = auth_status(Settings(provider="openai", api_format="openai_compat"))
    assert status == "configured"


def test_resolve_auth_status_prefers_env_source_over_loaded_api_key(monkeypatch) -> None:
    """当环境变量生效时，认证来源应显示为 env 而不是 settings。"""

    monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot-secret")
    info = resolve_auth_status(
        Settings(
            provider="moonshot",
            api_format="openai_compat",
            api_key="persisted-secret",
        )
    )
    assert info.status == "configured"
    assert info.source == "env:MOONSHOT_API_KEY"


def test_resolve_auth_status_falls_back_to_codex_auth_for_openai_provider(
    tmp_path: Path, monkeypatch
) -> None:
    """OpenAI 兼容 provider 在缺少环境变量时应回退到 Codex auth 文件。"""

    monkeypatch.setenv("HOME", str(tmp_path))
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "auth.json").write_text(
        json.dumps(
            {
                "OPENAI_API_KEY": "sk-codex-secret",
                "auth_mode": "apikey",
                "tokens": {},
            }
        ),
        encoding="utf-8",
    )

    info = resolve_auth_status(Settings(provider="openai", api_format="openai_compat"))

    assert info.status == "configured"
    assert info.source == "codex:~/.codex/auth.json#OPENAI_API_KEY"


def test_resolve_auth_status_does_not_use_codex_auth_for_anthropic_provider(
    tmp_path: Path, monkeypatch
) -> None:
    """Anthropic provider 不应错误复用 Codex 的 OpenAI key。"""

    monkeypatch.setenv("HOME", str(tmp_path))
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "auth.json").write_text(
        json.dumps({"OPENAI_API_KEY": "sk-codex-secret"}),
        encoding="utf-8",
    )

    info = resolve_auth_status(Settings(provider="anthropic", api_format="anthropic"))

    assert info.status == "missing"
    assert info.source == "missing"


def test_settings_resolve_api_key_falls_back_to_codex_auth_for_openai_provider(
    tmp_path: Path, monkeypatch
) -> None:
    """运行时取 key 时也应复用 Codex auth 回退逻辑。"""

    monkeypatch.setenv("HOME", str(tmp_path))
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "auth.json").write_text(
        json.dumps({"OPENAI_API_KEY": "sk-codex-secret"}),
        encoding="utf-8",
    )

    resolved = Settings(provider="openai", api_format="openai_compat").resolve_api_key()

    assert resolved == "sk-codex-secret"
