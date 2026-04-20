"""LLM 提供商注册表。

把 provider 的协议格式、默认网关和环境变量收敛到一处，
避免 CLI、状态展示和 runtime 选型各自维护一套不一致规则。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderSpec:
    """提供商元数据。

    描述 provider 是什么、默认走什么 API 格式、该读哪个环境变量，
    以及当用户只给了模型名或 base_url 时如何推断 provider。
    """

    name: str
    display_name: str
    api_format: str
    env_key: str
    default_base_url: str = ""
    model_keywords: tuple[str, ...] = ()
    base_url_keywords: tuple[str, ...] = ()
    api_key_prefixes: tuple[str, ...] = ()


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="anthropic",
        display_name="Anthropic",
        api_format="anthropic",
        env_key="ANTHROPIC_API_KEY",
        model_keywords=("claude", "anthropic", "sonnet", "opus", "haiku"),
    ),
    ProviderSpec(
        name="openai",
        display_name="OpenAI",
        api_format="openai_compat",
        env_key="OPENAI_API_KEY",
        model_keywords=("gpt", "openai", "o1", "o3", "o4"),
    ),
    ProviderSpec(
        name="moonshot",
        display_name="Moonshot",
        api_format="openai_compat",
        env_key="MOONSHOT_API_KEY",
        default_base_url="https://api.moonshot.ai/v1",
        model_keywords=("moonshot", "kimi"),
        base_url_keywords=("moonshot",),
    ),
    ProviderSpec(
        name="dashscope",
        display_name="DashScope",
        api_format="openai_compat",
        env_key="DASHSCOPE_API_KEY",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_keywords=("qwen", "dashscope"),
        base_url_keywords=("dashscope", "aliyuncs"),
    ),
    ProviderSpec(
        name="gemini",
        display_name="Gemini",
        api_format="openai_compat",
        env_key="GEMINI_API_KEY",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model_keywords=("gemini",),
        base_url_keywords=("googleapis", "generativelanguage"),
    ),
    ProviderSpec(
        name="deepseek",
        display_name="DeepSeek",
        api_format="openai_compat",
        env_key="DEEPSEEK_API_KEY",
        default_base_url="https://api.deepseek.com/v1",
        model_keywords=("deepseek",),
        base_url_keywords=("deepseek",),
    ),
    ProviderSpec(
        name="minimax",
        display_name="MiniMax",
        api_format="openai_compat",
        env_key="MINIMAX_API_KEY",
        default_base_url="https://api.minimax.io/v1",
        model_keywords=("minimax",),
        base_url_keywords=("minimax",),
    ),
    ProviderSpec(
        name="zhipu",
        display_name="Zhipu AI",
        api_format="openai_compat",
        env_key="ZHIPUAI_API_KEY",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        model_keywords=("glm", "chatglm", "zhipu"),
        base_url_keywords=("bigmodel", "zhipu"),
    ),
    ProviderSpec(
        name="groq",
        display_name="Groq",
        api_format="openai_compat",
        env_key="GROQ_API_KEY",
        default_base_url="https://api.groq.com/openai/v1",
        model_keywords=("groq",),
        base_url_keywords=("groq",),
        api_key_prefixes=("gsk_",),
    ),
    ProviderSpec(
        name="openrouter",
        display_name="OpenRouter",
        api_format="openai_compat",
        env_key="OPENROUTER_API_KEY",
        default_base_url="https://openrouter.ai/api/v1",
        model_keywords=("openrouter",),
        base_url_keywords=("openrouter",),
        api_key_prefixes=("sk-or-",),
    ),
)


def list_provider_specs() -> tuple[ProviderSpec, ...]:
    """返回所有内置 provider。

    供 CLI 列表页和测试复用，避免散落的硬编码 provider 列表。
    """

    return PROVIDERS


def get_provider_spec(name: str | None) -> ProviderSpec | None:
    """按名称查找 provider 元数据。"""

    if not name:
        return None
    normalized = name.strip().lower()
    for spec in PROVIDERS:
        if spec.name == normalized:
            return spec
    return None


def infer_provider_spec(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> ProviderSpec:
    """根据显式配置和线索推断当前 provider。

    优先级是显式 provider 名称，其次是 base_url、API key 前缀和模型名，
    最后再退回 API 格式默认值，保证没有 provider 配置时也能稳定工作。
    """

    explicit = get_provider_spec(provider_name)
    if explicit is not None:
        return explicit

    normalized_base_url = (base_url or "").strip().lower()
    if normalized_base_url:
        for spec in PROVIDERS:
            if any(keyword in normalized_base_url for keyword in spec.base_url_keywords):
                return spec

    normalized_api_key = (api_key or "").strip()
    if normalized_api_key:
        for spec in PROVIDERS:
            if any(normalized_api_key.startswith(prefix) for prefix in spec.api_key_prefixes):
                return spec

    normalized_model = (model or "").strip().lower()
    if normalized_model:
        for spec in PROVIDERS:
            if any(keyword in normalized_model for keyword in spec.model_keywords):
                return spec

    if api_format == "openai_compat":
        fallback = get_provider_spec("openai")
        assert fallback is not None
        return fallback

    fallback = get_provider_spec("anthropic")
    assert fallback is not None
    return fallback


def resolve_api_key_from_env(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> str:
    """按 provider 语义从环境变量解析 API key。

    会同时兼容 `VELARIS_*`、`OPENHARNESS_*` 和 provider 自己的环境变量，
    这样品牌升级后旧配置仍可继续工作。
    """

    _env_name, env_value = resolve_api_key_source_from_env(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    return env_value


def _should_use_codex_openai_key(spec: ProviderSpec) -> bool:
    """判断当前 provider 是否允许回退到 Codex 的 OpenAI key。

    目前只对真正的 OpenAI provider 生效，避免把 Codex 登录产生的
    `OPENAI_API_KEY` 误用到 Moonshot / DashScope 等 vendor-specific 网关。
    """

    return spec.name == "openai"


def _get_codex_auth_file_path() -> Path:
    """返回 Codex 鉴权文件路径。

    优先读取 `CODEX_HOME`，否则退回到默认的 `~/.codex/auth.json`。
    """

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "auth.json"
    return Path.home() / ".codex" / "auth.json"


def _render_home_relative_path(path: Path) -> str:
    """把路径渲染为尽量稳定的人类可读格式。"""

    home = Path.home()
    try:
        relative = path.relative_to(home)
    except ValueError:
        return path.as_posix()
    return f"~/{relative.as_posix()}"


def resolve_api_key_source_from_codex(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> tuple[str, str]:
    """按 provider 语义从 Codex auth 文件读取可复用的 API key。

    这是一个只读回退路径：只有在当前 provider 可以安全复用 Codex 的
    `OPENAI_API_KEY` 时才会尝试读取，并且任何文件缺失/格式异常都会静默跳过。
    """

    spec = infer_provider_spec(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    if not _should_use_codex_openai_key(spec):
        return "", ""

    auth_path = _get_codex_auth_file_path()
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return "", ""
    if not isinstance(payload, dict):
        return "", ""

    candidate = payload.get("OPENAI_API_KEY")
    if not isinstance(candidate, str) or not candidate:
        return "", ""

    return f"codex:{_render_home_relative_path(auth_path)}#OPENAI_API_KEY", candidate


def resolve_api_key(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> str:
    """按统一优先级解析可直接使用的 API key。

    当前顺序为：环境变量 → Codex auth 文件 → 空字符串。
    `settings.api_key` 的优先级仍由调用方自行决定。
    """

    _source, value = resolve_api_key_source(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    return value


def resolve_api_key_source(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> tuple[str, str]:
    """按统一优先级返回命中的凭据来源和值。"""

    env_name, env_value = resolve_api_key_source_from_env(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    if env_value:
        return f"env:{env_name}", env_value

    codex_source, codex_value = resolve_api_key_source_from_codex(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    if codex_value:
        return codex_source, codex_value

    return "", ""


def resolve_api_key_source_from_env(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
) -> tuple[str, str]:
    """按 provider 语义返回命中的环境变量名和值。

    会同时兼容 `VELARIS_*`、`OPENHARNESS_*` 和 provider 自己的环境变量，
    这样品牌升级后旧配置仍可继续工作。
    """

    spec = infer_provider_spec(
        provider_name=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_format=api_format,
    )
    names: list[str] = ["VELARIS_API_KEY", "OPENHARNESS_API_KEY"]
    if spec.env_key:
        names.append(spec.env_key)
    if spec.api_format == "openai_compat":
        names.append("OPENAI_API_KEY")
    names.append("ANTHROPIC_API_KEY")

    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        value = os.environ.get(name, "")
        if value:
            return name, value
    return "", ""
