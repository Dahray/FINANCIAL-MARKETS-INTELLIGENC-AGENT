"""
Google Gemini LLM Client Wrapper with Pydantic Structured Output Validation.
Enforces strict adherence to Agent 6 quantitative artifacts and Source Register UUID citations.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.agents.llm")

T = TypeVar("T", bound=BaseModel)


class GeminiResearchClient:
    """
    Wrapper around Google Gemini (`google-genai` SDK) for institutional research synthesis.
    Never permits the LLM to invent numerical calculations: all quantitative metrics must
    be passed in the prompt context from Agent 6's deterministic Python calculations.
    """

    @staticmethod
    def is_live_api_configured() -> bool:
        return bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10)

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
        Generate a Pydantic-validated structured output using Google Gemini API when
        `GEMINI_API_KEY` is configured, falling back to `deterministic_builder` (which
        synthesizes directly from verified database & Agent 6 quantitative records)
        if API credentials are not yet set or if network/quota errors occur.
        """
        if cls.is_live_api_configured():
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = (
                    settings.GEMINI_FAST_MODEL
                    if use_fast_model
                    else settings.GEMINI_PRIMARY_MODEL
                )
                resp = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=settings.GEMINI_TEMPERATURE,
                        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )
                if resp.text:
                    data = json.loads(resp.text)
                    return response_schema.model_validate(data)
            except Exception as exc:
                logger.warning(
                    "Gemini structured generation note (using deterministic evidence synthesizer): %s",
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
        """Generate citation-backed research prose via Gemini or deterministic evidence builder."""
        if cls.is_live_api_configured():
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = (
                    settings.GEMINI_FAST_MODEL
                    if use_fast_model
                    else settings.GEMINI_PRIMARY_MODEL
                )
                resp = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=settings.GEMINI_TEMPERATURE,
                        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                    ),
                )
                if resp.text:
                    return resp.text.strip()
            except Exception as exc:
                logger.warning("Gemini text generation note: %s", exc)

        return deterministic_fallback_fn()
