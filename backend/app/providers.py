"""LLM backends. Pick one with AIGREE_PROVIDER in backend/.env.

- ollama : local models via Ollama (free, e.g. Qwen). Uses Ollama's native API so we can
           set the context size, turn off "thinking", and enforce the JSON schema.
- openai : OpenAI or any OpenAI-compatible API (Alibaba Qwen / DashScope, OpenRouter, ...).
- claude : Anthropic Claude API.

Every provider returns a Completion and turns its own SDK errors into AnalysisError,
so the rest of the app doesn't care which one is in use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from . import config


class AnalysisError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class Completion:
    text: str
    stop: str  # "end" | "max_tokens" | "refusal"
    assistant_message: dict[str, Any]  # appended to the conversation when retrying


class Provider(Protocol):
    async def complete(self, system: str, messages: list[dict], schema: dict) -> Completion: ...


def schema_instructions(schema: dict) -> str:
    """Appended to the system prompt for models without guaranteed schema support."""
    return (
        "\n\n## Output format\n"
        "Reply with one JSON object only (no markdown, no commentary) that matches this JSON Schema:\n"
        f"{json.dumps(schema, separators=(',', ':'))}"
    )


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------


class OllamaProvider:
    def __init__(self) -> None:
        self.url = config.BASE_URL.rstrip("/") + "/api/chat"
        self.http = httpx.AsyncClient(timeout=config.TIMEOUT_SECONDS)

    async def complete(self, system: str, messages: list[dict], schema: dict) -> Completion:
        body: dict[str, Any] = {
            "model": config.MODEL,
            "stream": False,
            "format": schema,  # Ollama constrains the output to this JSON schema
            "options": {"num_ctx": config.OLLAMA_NUM_CTX, "temperature": 0.2},
            "messages": [{"role": "system", "content": system + schema_instructions(schema)}, *messages],
        }
        if config.OLLAMA_THINK is not None:
            body["think"] = config.OLLAMA_THINK
        try:
            r = await self.http.post(self.url, json=body)
        except httpx.ConnectError:
            raise AnalysisError(
                f"Can't reach Ollama at {config.BASE_URL}. Start the Ollama app, then try again.", 503
            )
        except httpx.TimeoutException:
            raise AnalysisError(
                f"The local model took longer than {config.TIMEOUT_SECONDS}s. "
                "Try a smaller model or a shorter document.", 504
            )
        if r.status_code == 404:
            raise AnalysisError(
                f"Ollama model '{config.MODEL}' isn't downloaded. Run: ollama pull {config.MODEL}", 500
            )
        if r.status_code != 200:
            raise AnalysisError(f"Ollama error {r.status_code}: {r.text[:300]}", 502)
        data = r.json()
        text = data.get("message", {}).get("content", "")
        stop = "max_tokens" if data.get("done_reason") == "length" else "end"
        return Completion(text, stop, {"role": "assistant", "content": text})


# ---------------------------------------------------------------------------
# OpenAI and OpenAI-compatible APIs (Alibaba Qwen, OpenRouter, ...)
# ---------------------------------------------------------------------------


class OpenAICompatProvider:
    def __init__(self) -> None:
        import openai

        self.openai = openai
        if not config.API_KEY:
            raise AnalysisError("Server misconfigured: set AIGREE_API_KEY in backend/.env.", 500)
        self.client = openai.AsyncOpenAI(
            api_key=config.API_KEY,
            base_url=config.BASE_URL or None,
            timeout=config.TIMEOUT_SECONDS,
            max_retries=2,
        )

    def _response_format(self, schema: dict) -> dict:
        if config.JSON_MODE == "json_schema":
            return {"type": "json_schema", "json_schema": {"name": "result", "schema": schema, "strict": True}}
        return {"type": "json_object"}

    async def complete(self, system: str, messages: list[dict], schema: dict) -> Completion:
        oa = self.openai
        try:
            resp = await self.client.chat.completions.create(
                model=config.MODEL,
                messages=[{"role": "system", "content": system + schema_instructions(schema)}, *messages],
                response_format=self._response_format(schema),
            )
        except oa.AuthenticationError:
            raise AnalysisError("Invalid API key. Check AIGREE_API_KEY in backend/.env.", 500)
        except oa.RateLimitError:
            raise AnalysisError("Rate limited or out of credits/free quota. Try again later.", 429)
        except oa.NotFoundError:
            raise AnalysisError(f"Model '{config.MODEL}' not found at {config.BASE_URL or 'OpenAI'}.", 500)
        except oa.BadRequestError as e:
            raise AnalysisError(f"The AI service rejected the request: {e.message}", 502)
        except oa.APITimeoutError:
            raise AnalysisError("The AI service timed out. Try a shorter document.", 504)
        except oa.APIConnectionError:
            raise AnalysisError("Could not reach the AI service. Check your internet connection.", 503)
        except oa.APIStatusError as e:
            raise AnalysisError(f"The AI service returned an error ({e.status_code}). Try again shortly.", 502)

        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        if getattr(msg, "refusal", None) or choice.finish_reason == "content_filter":
            stop = "refusal"
        elif choice.finish_reason == "length":
            stop = "max_tokens"
        else:
            stop = "end"
        return Completion(text, stop, {"role": "assistant", "content": text})


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeProvider:
    def __init__(self) -> None:
        import anthropic

        self.anthropic = anthropic
        self.client = anthropic.AsyncAnthropic(api_key=config.API_KEY or None)

    async def complete(self, system: str, messages: list[dict], schema: dict) -> Completion:
        an = self.anthropic
        kwargs = dict(
            model=config.MODEL,
            max_tokens=config.MAX_OUTPUT_TOKENS,
            system=system,
            messages=messages,
            output_config={"effort": config.EFFORT, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if config.USE_FALLBACKS:
                resp = await self.client.beta.messages.create(**kwargs, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                resp = await self.client.messages.create(**kwargs)
        except an.AuthenticationError:
            raise AnalysisError("Invalid API key. Check ANTHROPIC_API_KEY in backend/.env.", 500)
        except an.RateLimitError:
            raise AnalysisError("Too many requests to the AI service. Try again in a minute.", 429)
        except an.BadRequestError as e:
            raise AnalysisError(f"The AI service rejected the request: {e.message}", 502)
        except an.APIStatusError as e:
            raise AnalysisError(f"The AI service returned an error ({e.status_code}). Try again shortly.", 502)
        except an.APIConnectionError:
            raise AnalysisError("Could not reach the AI service. Check your internet connection.", 503)
        except TypeError as e:  # the SDK raises TypeError when no credentials are configured
            if "authentication" not in str(e).lower():
                raise
            raise AnalysisError("Server misconfigured: set ANTHROPIC_API_KEY in backend/.env.", 500)

        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        stop = {"refusal": "refusal", "max_tokens": "max_tokens"}.get(resp.stop_reason, "end")
        return Completion(text, stop, {"role": "assistant", "content": resp.content})


def make_provider() -> Provider:
    if config.PROVIDER == "ollama":
        return OllamaProvider()
    if config.PROVIDER == "openai":
        return OpenAICompatProvider()
    if config.PROVIDER == "claude":
        return ClaudeProvider()
    raise AnalysisError(f"Unknown AIGREE_PROVIDER '{config.PROVIDER}'. Use ollama, openai, or claude.", 500)
