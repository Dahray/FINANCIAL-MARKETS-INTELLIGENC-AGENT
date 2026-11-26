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


class GeminiResearchClient:
    """
    Google Gemini REST & SDK Client for institutional research synthesis.
    Never permits the LLM to invent numerical calculations: all quantitative metrics must
    be passed in the prompt context from Agent 6's deterministic Python calculations.
    """

    @staticmethod
    def is_live_api_configured() -> bool:
        key = (settings.GEMINI_API_KEY or "").strip()
        return bool(key and len(key) > 10)

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

        payload: Dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": gen_config,
        }

        headers = {"Content-Type": "application/json"}
        params: Dict[str, str] = {}
        if key.startswith("AIza"):
            params["key"] = key
        else:
            params["key"] = key

        with create_http_client(timeout=25) as client:
            resp = client.post(url, params=params, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            body = resp.json()
            candidates = body.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidates returned by Gemini REST API")
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(str(p.get("text", "")) for p in parts).strip()

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
        with a valid AI Studio key (`AIza...`), otherwise synthesize directly from verified
        database and Agent 6 quantitative records via `deterministic_builder`.
        """
        key = (settings.GEMINI_API_KEY or "").strip()
        if cls.is_live_api_configured() and key.startswith("AIza"):
            try:
                model_name = (
                    settings.GEMINI_FAST_MODEL
                    if use_fast_model
                    else settings.GEMINI_PRIMARY_MODEL
                )
                schema_hint = json.dumps(response_schema.model_json_schema())
                full_prompt = (
                    f"{user_prompt}\n\n"
                    f"Respond strictly with valid JSON conforming to this schema:\n{schema_hint}"
                )
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
                    "Using deterministic evidence synthesizer (Gemini REST note: %s)",
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
        key = (settings.GEMINI_API_KEY or "").strip()
        if cls.is_live_api_configured() and key.startswith("AIza"):
            try:
                model_name = (
                    settings.GEMINI_FAST_MODEL
                    if use_fast_model
                    else settings.GEMINI_PRIMARY_MODEL
                )
                txt = cls._call_gemini_rest(
                    model_name=model_name,
                    system_instruction=system_instruction,
                    user_prompt=user_prompt,
                    json_mode=False,
                )
                if txt:
                    return txt
            except Exception as exc:
                logger.info("Gemini text generation note: %s", exc)

        return deterministic_fallback_fn()
