"""
llm_router.py - Fail-fast routing across free-tier LLM providers.

The AI Director only writes words, so the game must never wait on it. Each kind
of call has an ordered list of routes ("provider:model"). A route is tried once,
with a short timeout and no hidden retries. A rate-limited, overloaded or retired
route is put on cooldown and skipped until it recovers, so a busy table falls
through to the next provider (and finally to authored text) in milliseconds
instead of sleeping on a 429.

Free-tier facts this is built around (measured 2026-11):
  * Groq: each model has its own quota (8,000 tokens/min, 1,000 requests/day).
    qwen3.8-27b answers in ~0.6s without hidden reasoning tokens; the gpt-oss
    models spend reasoning tokens, so they are asked for low effort.
  * Gemini flash-lite: 15 requests/min, large token allowance, ~2s.
"""
from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional, Tuple, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMUnavailable(Exception):
    """Every route failed or is cooling down."""


def parse_routes(spec: str) -> List[Tuple[str, str]]:
    routes = []
    for part in (spec or "").split(","):
        part = part.strip()
        if ":" in part:
            provider, model = part.split(":", 1)
            routes.append((provider.strip().lower(), model.strip()))
    return routes


def _retry_seconds(response: httpx.Response) -> float:
    header = response.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    match = re.search(r'retry(?:Delay"?:\s*"| in )([\d.]+)s', response.text or "")
    return float(match.group(1)) if match else 30.0


class LLMRouter:
    def __init__(self) -> None:
        self._http: Optional[httpx.AsyncClient] = None
        self._cooldown: Dict[Tuple[str, str], float] = {}
        self.stats: Dict[str, int] = {}

    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=8))
        return self._http

    def _count(self, key: str) -> None:
        self.stats[key] = self.stats.get(key, 0) + 1

    def _cool(self, route: Tuple[str, str], seconds: float, why: str) -> None:
        self._cooldown[route] = time.monotonic() + seconds
        print(f"[LLM] {route[0]}:{route[1]} cooling {seconds:.0f}s ({why})")

    async def _call(self, route: Tuple[str, str], prompt: str, system: Optional[str],
                    json_mode: bool, max_tokens: int, timeout: float) -> str:
        provider, model = route
        if provider == "groq":
            body = {
                "model": model,
                "messages": ([{"role": "system", "content": system}] if system else [])
                + [{"role": "user", "content": prompt}],
                "max_completion_tokens": max_tokens,
                "temperature": 0.8,
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            if "gpt-oss" in model:
                body["reasoning_effort"] = "low"  # reasoning tokens count against the 8k/min quota
            response = await self._client().post(
                GROQ_URL, json=body, timeout=timeout,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
        elif provider == "gemini":
            config = {"maxOutputTokens": max_tokens, "temperature": 0.8}
            if json_mode:
                config["responseMimeType"] = "application/json"
            body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            response = await self._client().post(
                GEMINI_URL.format(model=model), json=body, timeout=timeout,
                headers={"x-goog-api-key": settings.gemini_api_key},
            )
        else:
            raise ValueError(f"Unknown LLM provider '{provider}'")

        if response.status_code == 429:
            self._cool(route, min(_retry_seconds(response), 120.0), "rate limited")
            raise LLMUnavailable("429")
        if response.status_code == 404:
            self._cool(route, 3600.0, "model not found or retired; update the LLM_*_ROUTES settings")
            raise LLMUnavailable("404")
        if response.status_code >= 500:
            self._cool(route, 15.0, f"provider error {response.status_code}")
            raise LLMUnavailable(str(response.status_code))
        if response.status_code >= 400:
            self._cool(route, 5.0, f"request rejected {response.status_code}: {response.text[:120]}")
            raise LLMUnavailable(str(response.status_code))

        data = response.json()
        if provider == "groq":
            text = data["choices"][0]["message"].get("content") or ""
        else:
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts)
        if not text.strip():
            raise LLMUnavailable("empty response")
        return text

    async def text(self, routes_spec: str, prompt: str, system: Optional[str] = None,
                   json_mode: bool = False, max_tokens: int = 700, timeout: float = 12.0) -> str:
        """Return the first successful completion, trying each available route once."""
        now = time.monotonic()
        for route in parse_routes(routes_spec):
            if self._cooldown.get(route, 0.0) > now:
                self._count("skipped_cooldown")
                continue
            try:
                result = await self._call(route, prompt, system, json_mode, max_tokens, timeout)
                self._count(f"ok:{route[0]}:{route[1]}")
                return result
            except LLMUnavailable:
                self._count(f"fail:{route[0]}:{route[1]}")
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                self._count(f"fail:{route[0]}:{route[1]}")
                self._cool(route, 10.0, f"{type(exc).__name__}")
        self._count("exhausted")
        raise LLMUnavailable("no LLM route available")

    async def structured(self, routes_spec: str, prompt: str, model: Type[T],
                         system: Optional[str] = None, max_tokens: int = 700, timeout: float = 12.0) -> T:
        """JSON-mode completion validated against a pydantic model; a bad payload moves on to the next route."""
        last_error: Exception = LLMUnavailable("no LLM route available")
        for route in parse_routes(routes_spec):
            spec = f"{route[0]}:{route[1]}"
            try:
                raw = await self.text(spec, prompt, system, json_mode=True, max_tokens=max_tokens, timeout=timeout)
            except LLMUnavailable as exc:
                last_error = exc
                continue
            start, end = raw.find("{"), raw.rfind("}")
            try:
                return model.model_validate(json.loads(raw[start:end + 1]))
            except (ValidationError, ValueError) as exc:
                self._count(f"invalid_json:{spec}")
                last_error = exc
        raise LLMUnavailable(str(last_error)[:200])


llm_router = LLMRouter()
