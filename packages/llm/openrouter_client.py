"""Thin OpenRouter client with model selection per workload.

Workloads:
  - build:    der tägliche Agent (Hermes 4 70B als Primary — gutes Deutsch + Code)
  - care:     produktive Pflege-Unterstützung (Latenz, gutes Deutsch)
  - legal:    monatlicher Audit (stärker, eigener Topf)

Modell-Konfiguration:
  - Aktives Build-Modell steht in MODEL_CONFIG_FILE (packages/llm/model_config.json)
  - Wöchentlicher Check (scripts/check_model_updates.py) überschreibt bei neuerer Version
  - Fallback: Werte in dieser Datei greifen wenn JSON fehlt

Niemals direkt aufrufen ohne BudgetGuard!
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_CONFIG_FILE = Path(__file__).parent / "model_config.json"


class ModelChoice(str, Enum):
    """Rollen, nicht Modelle. Welches Modell eine Rolle ausfüllt, steht in
    model_config.json — der wöchentliche Check tauscht es aus, wenn ein
    Anbieter ein Modell einstellt. Die Werte hier sind nur der Notfall-Fallback.

    Grundsatz: Gebaut wird mit Modellen mit offenen Gewichten (offene Software
    aus offenen Modellen). Recherche und Rechtsprüfung laufen selten und
    dürfen ein stärkeres Modell nutzen — eigener Budget-Topf.
    """
    BUILD_PRIMARY = "deepseek/deepseek-v4-pro"
    BUILD_ESCALATION = "moonshotai/kimi-k2.7-code"
    BUILD_CHEAP   = "qwen/qwen3-coder-next"
    CARE_PRIMARY  = "deepseek/deepseek-v4-pro"
    CARE_CHEAP    = "qwen/qwen3-coder-next"
    LEGAL         = "anthropic/claude-sonnet-5.5"
    RESEARCH      = "anthropic/claude-sonnet-5.5"


def _load_config() -> dict:
    if MODEL_CONFIG_FILE.exists():
        try:
            return json.loads(MODEL_CONFIG_FILE.read_text()).get("roles", {})
        except json.JSONDecodeError:
            pass
    return {}


def get_model(role: "ModelChoice") -> str:
    """Modell-ID für eine Rolle — aus model_config.json, sonst Fallback."""
    return _load_config().get(role.name.lower(), role.value)


def get_active_build_model() -> str:
    return get_model(ModelChoice.BUILD_PRIMARY)


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
        model_id = get_model(model) if isinstance(model, ModelChoice) else model

        body = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "usage": {"include": True},
        }
        if extra:
            body.update(extra)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pflegeos.vercel.app",
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
            model=data.get("model", model_id),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=cost,
        )

    @staticmethod
    def estimate_cost(model: ModelChoice | str, prompt_tokens: int, completion_tokens: int) -> float:
        """Best-Effort-Schätzung — wird nach Call durch tatsächliche Kosten ersetzt."""
        # Preise pro 1M Tokens (Stand 2026-10, in USD)
        pricing: dict[str, tuple[float, float]] = {
            "deepseek/deepseek-v4-pro":      (0.21, 0.42),
            "moonshotai/kimi-k2.7-code":     (0.67, 3.35),
            "qwen/qwen3-coder-next":         (0.12, 0.80),
            "anthropic/claude-sonnet-5.5":   (2.00, 10.00),
        }
        m = get_model(model) if isinstance(model, ModelChoice) else model
        p_in, p_out = pricing.get(m, (0.5, 1.5))
        return (prompt_tokens / 1_000_000) * p_in + (completion_tokens / 1_000_000) * p_out
