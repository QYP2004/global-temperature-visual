"""LLM client abstraction.

The API key is read ONLY from the server-side environment and never sent to the
browser. The class is intentionally small and injectable so the core agents can
be unit-tested against a fake.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional, Protocol

from dotenv import load_dotenv

load_dotenv()


class LLMError(RuntimeError):
    pass


def _friendly_llm_error(exc: Exception, timeout: float) -> str:
    """Translate raw SDK/network exceptions into actionable Chinese messages."""
    try:
        import httpx
        import openai
    except ImportError:  # pragma: no cover
        return f"大模型调用失败：{exc}"
    if isinstance(exc, (openai.APITimeoutError, httpx.TimeoutException)):
        return (f"请求大模型超时（超过 {timeout:.0f} 秒）。请检查网络，或确认 LLM_BASE_URL "
                f"指向的服务当前可达；可调大环境变量 LLM_TIMEOUT 后重试。")
    if isinstance(exc, (openai.APIConnectionError, httpx.ConnectError)):
        return ("无法连接大模型服务，请检查 LLM_BASE_URL 与网络（国内直连 api.openai.com "
                "通常需要代理，可改用 DeepSeek / Moonshot 等可达端点）。")
    if isinstance(exc, openai.AuthenticationError):
        return "API Key 无效或已失效，请检查 LLM_API_KEY。"
    if isinstance(exc, openai.RateLimitError):
        return "大模型服务触发限流，请稍后再试。"
    return f"大模型调用失败：{exc}"


def _parse_json(text: str) -> dict:
    """Extract a JSON object from an LLM reply, tolerating ```json fences and prose."""
    if text is None:
        raise LLMError("empty LLM response")
    t = text.strip()
    # Strip code fences.
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # Fall back: grab the outermost {...} block.
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"could not parse JSON from LLM: {exc}") from exc
    raise LLMError("no JSON object found in LLM response")


class LLMClient(Protocol):
    async def chat_json(self, system: str, user: str) -> dict: ...

    async def chat_text(self, system: str, user: str) -> str: ...


class OpenAILLM:
    """Real client using the OpenAI-compatible SDK."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, temperature: float = 0.8,
                 timeout: float = 60.0, max_retries: int = 1):
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.timeout = float(os.environ.get("LLM_TIMEOUT", timeout))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", max_retries))
        # Some local relays (e.g. Codex) only speak the Responses API.
        self.wire_api = (os.environ.get("LLM_WIRE_API") or "chat").strip().lower()
        self._client = None
        if self.api_key:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

    async def _chat(self, system: str, user: str) -> str:
        if self._client is None:
            raise LLMError(
                "未配置 LLM_API_KEY。请复制 .env.example 为 .env 并填入有效 Key 后重启服务。"
            )
        try:
            if self.wire_api == "responses":
                text = await self._chat_responses(system, user)
            else:
                text = await self._chat_completions(system, user)
        except Exception as exc:
            raise LLMError(_friendly_llm_error(exc, self.timeout)) from exc
        if not text or not text.strip():
            raise LLMError("大模型返回了空内容，请重试。")
        return text

    async def _chat_completions(self, system: str, user: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
        )
        content = resp.choices[0].message.content
        return content or ""

    async def _chat_responses(self, system: str, user: str) -> str:
        max_tokens = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", 2048))
        resp = await self._client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_output_tokens=max_tokens,
        )
        # Output items: {"type":"reasoning", ...} and {"type":"message",
        # "content":[{"type":"output_text","text":...}]}. We want the message.
        texts = []
        for item in getattr(resp, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "output_text":
                    texts.append(part.text)
        return "".join(texts)

    async def chat_json(self, system: str, user: str) -> dict:
        return _parse_json(await self._chat(system, user))

    async def chat_text(self, system: str, user: str) -> str:
        return (await self._chat(system, user)).strip()


# Module-level singleton, configured at app startup.
_default_client: Optional[LLMClient] = None


def configure_llm(client: Optional[LLMClient] = None) -> LLMClient:
    global _default_client
    if client is not None:
        _default_client = client
        return client
    # Demo / offline mode: zero external dependency (no API key needed).
    if os.environ.get("LLM_DEMO", "").strip().lower() in ("1", "true", "yes", "on"):
        from .agents.demo_llm import DemoLLM
        _default_client = DemoLLM()
        return _default_client
    _default_client = OpenAILLM()
    return _default_client


def get_llm() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = OpenAILLM()
    return _default_client
