"""Thin OpenRouter client with model selection per workload.

Workloads:
  - build:    der tägliche Agent (preisgünstig, ausreichend kompetent)
  - care:     produktive Pflege-Unterstützung (Latenz, gutes Deutsch)
  - legal:    monatlicher Audit (stärker, eigener Topf)

Niemals direkt aufrufen ohne BudgetGuard! Auch nicht "nur kurz für Tests".
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class ModelChoice(str, Enum):
    # Order matters: first = preferred, rest = fallbacks bei Budgetdruck
    BUILD_PRIMARY = "deepseek/deepseek-chat"
    BUILD_CHEAP = "google/gemini-flash-1.5"
    CARE_PRIMARY = "google/gemini-flash-1.5"
    CARE_CHEAP = "deepseek/deepseek-chat"
    LEGAL = "anthropic/claude-3.7-sonnet"


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, timeout_s: float = 60.0):
        self.api_key = api_key or os.environ["OPENROUTER_API_KEY"]
        self.timeout_s = timeout_s

    async def chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: ModelChoice | str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        extra: dict[str, Any] | None = None,
    ) -> LLMResponse:
        body = {
            "model": model.value if isinstance(model, ModelChoice) else model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "usage": {"include": True},  # cost field
        }
        if extra:
            body.update(extra)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pflegeos.de",
            "X-Title": "PflegeOS",
        }

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(OPENROUTER_URL, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        cost = float(usage.get("cost", 0.0))

        return LLMResponse(
            text=choice,
            model=data.get("model", str(model)),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=cost,
        )

    @staticmethod
    def estimate_cost(model: ModelChoice | str, prompt_tokens: int, completion_tokens: int) -> float:
        """Best-Effort-Schätzung — wird nach Call durch tatsächliche Kosten ersetzt."""
        # Preise pro 1M Tokens (Stand 2026-05, in USD). Bewusst grob.
        pricing = {
            ModelChoice.BUILD_PRIMARY.value: (0.14, 0.28),     # deepseek-chat
            ModelChoice.BUILD_CHEAP.value: (0.075, 0.30),       # gemini-flash-1.5
            ModelChoice.CARE_PRIMARY.value: (0.075, 0.30),
            ModelChoice.CARE_CHEAP.value: (0.14, 0.28),
            ModelChoice.LEGAL.value: (3.00, 15.00),             # claude-3.7-sonnet
        }
        m = model.value if isinstance(model, ModelChoice) else model
        p_in, p_out = pricing.get(m, (1.0, 3.0))
        return (prompt_tokens / 1_000_000) * p_in + (completion_tokens / 1_000_000) * p_out
