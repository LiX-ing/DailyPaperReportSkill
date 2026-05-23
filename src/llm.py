from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml


@dataclass
class LLMSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    api_style: str


def _read_shell_var_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            out[key] = value
    return out


def _local_shell_vars() -> dict[str, str]:
    home = Path.home()
    merged: dict[str, str] = {}
    for name in [".zhsrc", ".zshrc"]:
        merged.update(_read_shell_var_file(home / name))
    return merged


def _credentials_file_vars(root: Path | None = None) -> dict[str, str]:
    paths: list[Path] = []
    custom = os.getenv("SKILL_CREDENTIALS_PATH", "").strip()
    if custom:
        paths.append(Path(custom))
    if root is not None:
        paths.append(root / "config" / "credentials.yaml")
    paths.append(Path.cwd() / "config" / "credentials.yaml")
    for path in paths:
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        llm = data.get("llm", {})
        if not isinstance(llm, dict):
            llm = {}
        out: dict[str, str] = {}
        mapping: dict[str, Any] = {
            "SKILL_PROVIDER": llm.get("provider"),
            "SKILL_MODEL": llm.get("model"),
            "SKILL_AUTH_TOKEN": llm.get("api_key"),
            "SKILL_BASE_URL": llm.get("base_url"),
            "SKILL_API_STYLE": llm.get("api_style"),
            "LLM_PROVIDER": llm.get("provider"),
            "LLM_MODEL": llm.get("model"),
            "LLM_API_KEY": llm.get("api_key"),
            "LLM_BASE_URL": llm.get("base_url"),
            "LLM_API_STYLE": llm.get("api_style"),
            "ANTHROPIC_AUTH_TOKEN": llm.get("anthropic_auth_token"),
            "ANTHROPIC_BASE_URL": llm.get("anthropic_base_url"),
            "ANTHROPIC_MODEL": llm.get("anthropic_model"),
        }
        for k, v in mapping.items():
            if isinstance(v, str) and v.strip():
                out[k] = v.strip()
        return out
    return {}


def load_llm_settings(root: Path | None = None) -> LLMSettings:
    shell_vars = _local_shell_vars()
    file_vars = _credentials_file_vars(root=root)

    def _first(*names: str) -> str:
        for name in names:
            v = file_vars.get(name, "").strip()
            if v:
                return v
            v = os.getenv(name, "").strip()
            if v:
                return v
            v = shell_vars.get(name, "").strip()
            if v:
                return v
        return ""

    provider = _first("SKILL_PROVIDER", "LLM_PROVIDER").lower() or "local"

    model = (
        _first("SKILL_MODEL", "LLM_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL")
        or "gpt-4.1-mini"
    )
    api_key = _first(
        "SKILL_AUTH_TOKEN",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
    )
    base_url = _first("SKILL_BASE_URL", "LLM_BASE_URL", "ANTHROPIC_BASE_URL")
    api_style = (_first("SKILL_API_STYLE", "LLM_API_STYLE") or "auto").lower()

    # Auto-upgrade from local mode when compatible local shell auth exists.
    if provider == "local" and api_key and base_url:
        provider = "openai_compatible"

    return LLMSettings(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        api_style=api_style,
    )


class BaseLLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class LocalLLMClient(BaseLLMClient):
    def generate(self, prompt: str) -> str:
        # Local fallback: no external model call.
        return ""


class RequestsCompatibleClient(BaseLLMClient):
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def _build_chat_url(self) -> str:
        base = (self.settings.base_url or "").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def _resolve_model(self) -> str:
        model = (self.settings.model or "").strip()
        base = (self.settings.base_url or "").lower()
        # DeepSeek common safe default. Some custom names are not accepted by the API.
        if "api.deepseek.com" in base and model in {"deepseek-v4-flash", "deepseek-v4"}:
            print(
                "[warn] remapping unsupported deepseek model name to deepseek-chat.",
                f"from={model}",
                file=sys.stderr,
            )
            return "deepseek-chat"
        return model

    def generate(self, prompt: str) -> str:
        if not self.settings.base_url or not self.settings.api_key:
            return ""
        url = self._build_chat_url()
        model = self._resolve_model()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        connect_timeout = float(os.getenv("LLM_CONNECT_TIMEOUT_SEC", "10"))
        read_timeout = float(os.getenv("LLM_READ_TIMEOUT_SEC", "180"))
        last_err: Exception | None = None
        for i in range(2):
            try:
                resp = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=(connect_timeout, read_timeout),
                )
                # Print API-side error details for easier debugging.
                if resp.status_code >= 400:
                    body = resp.text[:500]
                    raise RuntimeError(f"http={resp.status_code} body={body}")
                data = resp.json()
                if isinstance(data, dict) and data.get("error"):
                    raise RuntimeError(f"api_error={data.get('error')}")
                choices = data.get("choices", []) if isinstance(data, dict) else []
                if not choices:
                    raise RuntimeError("empty choices")
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content.strip()
                if isinstance(content, list):
                    parts: list[str] = []
                    for part in content:
                        if isinstance(part, str):
                            parts.append(part)
                        elif isinstance(part, dict):
                            t = part.get("text")
                            if isinstance(t, str):
                                parts.append(t)
                    return "\n".join(x for x in parts if x).strip()
                raise RuntimeError("unsupported content shape")
            except Exception as e:
                last_err = e
                # Retry once for transient network timeout.
                if i == 0:
                    continue
        print(
            "[warn] compat_http request failed; fallback to local summary.",
            f"provider={self.settings.provider}",
            f"model={model}",
            f"url={url}",
            f"error={last_err}",
            file=sys.stderr,
        )
        return ""


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

        from openai import OpenAI

        kwargs = {"api_key": settings.api_key}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self.client = OpenAI(**kwargs)

    def generate(self, prompt: str) -> str:
        def _extract_chat_text(chat_resp: object) -> str:
            choices = getattr(chat_resp, "choices", None) or []
            if not choices:
                return ""
            msg = getattr(choices[0], "message", None)
            if msg is None:
                return ""
            content = getattr(msg, "content", None)
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        t = part.get("text")
                        if isinstance(t, str):
                            parts.append(t)
                    else:
                        t = getattr(part, "text", None)
                        if isinstance(t, str):
                            parts.append(t)
                return "\n".join(x for x in parts if x).strip()
            return ""

        prefer_chat = self.settings.api_style == "chat"

        if prefer_chat:
            try:
                chat_resp = self.client.chat.completions.create(
                    model=self.settings.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                text = _extract_chat_text(chat_resp)
                if text:
                    return text
                raise RuntimeError("chat.completions returned empty content")
            except Exception as e:
                print(
                    "[warn] Preferred chat.completions failed, will fallback to local summary.",
                    f"provider={self.settings.provider}",
                    f"model={self.settings.model}",
                    f"chat_error={e}",
                    file=sys.stderr,
                )
                return ""

        try:
            # First try Responses API (new-style OpenAI interface).
            resp = self.client.responses.create(
                model=self.settings.model,
                input=prompt,
                temperature=0.2,
            )
            text = (resp.output_text or "").strip()
            if text:
                return text
        except Exception as e1:
            # Continue to chat.completions fallback below.
            last_err = e1
        else:
            last_err = RuntimeError("Responses API returned empty output_text")

        try:
            # Fallback for providers that only support chat completions.
            chat_resp = self.client.chat.completions.create(
                model=self.settings.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            text = _extract_chat_text(chat_resp)
            if text:
                return text
            raise RuntimeError("chat.completions returned empty content")
        except Exception as e2:
            print(
                "[warn] LLM request failed; fallback to local summary.",
                f"provider={self.settings.provider}",
                f"model={self.settings.model}",
                f"responses_error={last_err}",
                f"chat_error={e2}",
                file=sys.stderr,
            )
            return ""


def build_llm_client(settings: LLMSettings) -> BaseLLMClient:
    provider = settings.provider

    if provider == "local":
        return LocalLLMClient()

    if provider == "compat_http":
        if not settings.api_key:
            print(
                "[warn] compat_http configured but api_key is empty; fallback to local summary.",
                file=sys.stderr,
            )
            return LocalLLMClient()
        return RequestsCompatibleClient(settings)

    if provider in {"openai", "openai_compatible"}:
        if not settings.api_key:
            print(
                "[warn] LLM provider configured but api_key is empty; fallback to local summary.",
                f"provider={provider}",
                file=sys.stderr,
            )
            return LocalLLMClient()
        try:
            return OpenAICompatibleClient(settings)
        except ImportError:
            print(
                "[warn] openai package not installed; fallback to compat_http client.",
                file=sys.stderr,
            )
            return RequestsCompatibleClient(settings)

    return LocalLLMClient()
