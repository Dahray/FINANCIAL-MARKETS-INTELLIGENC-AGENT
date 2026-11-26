"""
Google Gemini LLM Client Wrapper with Direct HTTPS REST & SDK Support.
Calls Google Gemini REST API (`generativelanguage.googleapis.com/v1beta`) via SSL-resilient
`create_http_client` so it works seamlessly even without `google-genai` installed in the venv,
and falls back to deterministic evidence synthesis whenever needed.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Type, TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.core.ssl_helper import create_http_client

logger = get_logger("fmip.agents.llm")

T = TypeVar("T", bound=BaseModel)

GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


RETIRED_GEMINI_MODELS = {
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
}


class GeminiResearchClient:
    """
    Google Gemini REST & SDK Client for institutional research synthesis.
    Never permits the LLM to invent numerical calculations: all quantitative metrics must
    be passed in the prompt context from Agent 6's deterministic Python calculations.
    """

    @staticmethod
    def is_live_api_configured() -> bool:
        key = (settings.GEMINI_API_KEY or "").strip()
        if not key or len(key) <= 10:
            return False
        lowered = key.lower()
        return not any(tok in lowered for tok in ("your-", "placeholder", "replace-me", "changeme"))

    @staticmethod
    def _candidate_models(use_fast_model: bool) -> list[str]:
        configured = (
            settings.GEMINI_FAST_MODEL if use_fast_model else settings.GEMINI_PRIMARY_MODEL
        ).replace("models/", "").strip()
        defaults = (
            ["gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]
            if use_fast_model
            else ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]
        )
        chain: list[str] = []
        if configured and configured not in RETIRED_GEMINI_MODELS:
            chain.append(configured)
        for m in defaults:
            if m not in chain:
                chain.append(m)
        return chain

    @classmethod
    def _call_gemini_rest(
        cls,
        model_name: str,
        system_instruction: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        """Invoke Google Gemini REST API (`generateContent`) directly over HTTPS."""
        key = settings.GEMINI_API_KEY.strip()
        url = f"{GEMINI_REST_BASE}/{model_name}:generateContent"
        gen_config: Dict[str, Any] = {
            "temperature": settings.GEMINI_TEMPERATURE,
            "maxOutputTokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        enforced_system = (
            "MANDATORY SOURCE-OF-TRUTH GOVERNANCE RULE:\n"
            "1. Never replace, contradict, or 'correct' financial figures provided in the user prompt "
            "using your internal pre-training knowledge (your training weights are outdated).\n"
            "2. Every macroeconomic rate, FX rate, yield, index level, and quantitative metric in the prompt "
            "was fetched from live Tier-1 official APIs (CBN, FRED, FMP, World Bank) and verified by our "
            "deterministic Python engine. Preserve those exact figures verbatim and cite their source.\n"
            "3. Never fabricate missing numbers; if a metric is marked STALE_ARCHIVAL_BASELINE or unavailable, "
            "explicitly disclose that status.\n\n"
            f"{system_instruction}"
        )

        payload: Dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": enforced_system}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": gen_config,
        }

        headers = {"Content-Type": "application/json"}
        params: Dict[str, str] = {"key": key}

        with create_http_client(timeout=30) as client:
            resp = client.post(url, params=params, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} ({model_name})")
            body = resp.json()
            candidates = body.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidates returned by Gemini REST API")
            parts = candidates[0].get("content", {}).get("parts", [])
            text_chunks = [
                str(p.get("text", ""))
                for p in parts
                if isinstance(p, dict) and not p.get("thought")
            ]
            return "".join(text_chunks).strip()

    @classmethod
    def generate_structured(
        cls,
        system_instruction: str,
        user_prompt: str,
        response_schema: Type[T],
        deterministic_builder: Callable[[], T],
        use_fast_model: bool = False,
    ) -> T:
        """
        Generate a Pydantic-validated structured output via Gemini REST API when configured
        with a valid Gemini API key (`AIza...` or `AQ....`), otherwise synthesize directly
        from verified database and Agent 6 quantitative records via `deterministic_builder`.
        """
        if cls.is_live_api_configured():
            schema_hint = json.dumps(response_schema.model_json_schema())
            full_prompt = (
                f"{user_prompt}\n\n"
                f"Respond strictly with valid JSON conforming to this schema:\n{schema_hint}"
            )
            for model_name in cls._candidate_models(use_fast_model):
                try:
                    raw_json = cls._call_gemini_rest(
                        model_name=model_name,
                        system_instruction=system_instruction,
                        user_prompt=full_prompt,
                        json_mode=True,
                    )
                    if raw_json:
                        return response_schema.model_validate(json.loads(raw_json))
                except Exception as exc:
                    logger.info(
                        "Gemini structured synthesis note on %s (trying next/fallback): %s",
                        model_name,
                        exc,
                    )

        return deterministic_builder()

    @classmethod
    def generate_text(
        cls,
        system_instruction: str,
        user_prompt: str,
        deterministic_fallback_fn: Callable[[], str],
        use_fast_model: bool = False,
    ) -> str:
        """Generate citation-backed research prose via Gemini REST API or deterministic evidence builder."""
        if cls.is_live_api_configured():
            for model_name in cls._candidate_models(use_fast_model):
                try:
                    txt = cls._call_gemini_rest(
                        model_name=model_name,
                        system_instruction=system_instruction,
                        user_prompt=user_prompt,
                        json_mode=False,
                    )
                    if txt:
                        return txt
                except Exception as exc:
                    logger.info("Gemini text generation note on %s: %s", model_name, exc)

        return deterministic_fallback_fn()
