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
    # Hermes 4 70B ist das aktuellste Hermes-Modell (Stand 2026-05)
    # Günstiger als Deepseek auf Prompt-Seite, sehr gutes Deutsch + Code
    BUILD_PRIMARY = "nousresearch/hermes-4-70b"
    BUILD_CHEAP   = "google/gemini-flash-1.5"    # Fallback wenn Budget knapp
    CARE_PRIMARY  = "nousresearch/hermes-4-70b"  # Gleiche Qualität wie Build
    CARE_CHEAP    = "google/gemini-flash-1.5"
    LEGAL         = "anthropic/claude-3.7-sonnet" # Jurist-Lauf (eigener Topf)


def get_active_build_model() -> str:
    """Liest aktives Build-Modell aus model_config.json.

    Erlaubt dem wöchentlichen Update-Check, das Modell zu wechseln ohne
    Code-Änderung. Fällt auf ModelChoice.BUILD_PRIMARY zurück wenn Datei fehlt.
    """
    if MODEL_CONFIG_FILE.exists():
        try:
            cfg = json.loads(MODEL_CONFIG_FILE.read_text())
            return cfg.get("build_primary", ModelChoice.BUILD_PRIMARY.value)
        except (json.JSONDecodeError, KeyError):
            pass
    return ModelChoice.BUILD_PRIMARY.value


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
        # Bei BUILD_PRIMARY dynamisch das konfigurierte Modell nutzen
        if isinstance(model, ModelChoice) and model == ModelChoice.BUILD_PRIMARY:
            model_id = get_active_build_model()
        else:
            model_id = model.value if isinstance(model, ModelChoice) else model

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
        # Preise pro 1M Tokens (Stand 2026-05, in USD)
        pricing: dict[str, tuple[float, float]] = {
            "nousresearch/hermes-4-70b":         (0.130, 0.400),  # Hermes 4 70B
            "nousresearch/hermes-4-405b":        (1.000, 3.000),  # Hermes 4 405B
            "nousresearch/hermes-3-llama-3.1-70b": (0.700, 0.700),
            "google/gemini-flash-1.5":           (0.075, 0.300),
            "deepseek/deepseek-chat":            (0.140, 0.280),
            "anthropic/claude-3.7-sonnet":       (3.000, 15.000),
        }
        m = model.value if isinstance(model, ModelChoice) else model
        # Auch für dynamisch geladene Modelle
        if m == ModelChoice.BUILD_PRIMARY.value:
            m = get_active_build_model()
        p_in, p_out = pricing.get(m, (0.5, 1.5))
        return (prompt_tokens / 1_000_000) * p_in + (completion_tokens / 1_000_000) * p_out
