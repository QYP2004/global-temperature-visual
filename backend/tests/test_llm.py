"""Tests for LLM client error handling (timeout / connectivity / missing key)."""
import pytest

from backend.llm import LLMError, OpenAILLM, _friendly_llm_error


def test_missing_key_raises_clear_message(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = OpenAILLM(api_key=None)
    with pytest.raises(LLMError) as ei:
        # OpenAILLM without a key never builds a client, so _chat fails fast.
        import asyncio
        asyncio.run(llm._chat("s", "u"))
    assert "LLM_API_KEY" in str(ei.value)


def test_friendly_message_for_timeout():
    import httpx
    msg = _friendly_llm_error(httpx.ReadTimeout("request timed out"), timeout=60)
    assert "超时" in msg and "LLM_TIMEOUT" in msg


def test_friendly_message_for_connection_error():
    import httpx
    msg = _friendly_llm_error(httpx.ConnectError("refused"), timeout=60)
    assert "无法连接" in msg and "LLM_BASE_URL" in msg


def test_friendly_message_falls_back():
    msg = _friendly_llm_error(ValueError("weird"), timeout=60)
    assert "大模型调用失败" in msg
