"""Security utilities: JWT auth, RBAC, password hashing, and Prompt Injection Sanitizer."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import jwt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.security")


class UserRole(str, Enum):
    """Institutional Role-Based Access Control (RBAC) roles."""

    EXECUTIVE_ADMIN = "EXECUTIVE_ADMIN"
    RESEARCH_ANALYST = "RESEARCH_ANALYST"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    BOARD_VIEWER = "BOARD_VIEWER"


# ------------------------------------------------------------------------------
# 1. Cryptographic Password Hashing (OWASP PBKDF2-HMAC-SHA256, 310,000 iterations)
# ------------------------------------------------------------------------------
PBKDF2_ITERATIONS = 310_000


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a random 16-byte salt."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    dk_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${dk_b64}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash."""
    try:
        algorithm, iter_str, salt_b64, dk_b64 = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_dk = base64.b64decode(dk_b64.encode("ascii"))
        candidate_dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate_dk, expected_dk)
    except Exception:
        return False


# ------------------------------------------------------------------------------
# 2. JWT Token Generation & Validation
# ------------------------------------------------------------------------------
def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: str) -> str:
    """Create a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token. Raises jwt.PyJWTError on invalid/expired tokens."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ------------------------------------------------------------------------------
# 3. Untrusted External Content & Prompt Injection Sanitizer (Section 10 Mandate)
# ------------------------------------------------------------------------------
@dataclass
class SanitizedContentResult:
    """Result of sanitizing untrusted external text from web pages or PDFs."""

    clean_text: str
    wrapped_evidence_block: str
    injection_detected: bool
    matched_patterns: List[str]


class PromptInjectionSanitizer:
    """
    Protects FMIP agents from indirect prompt injection embedded in external websites,
    news articles, or scraped PDF documents.
    """

    INJECTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
        (
            "ignore_instructions",
            re.compile(
                r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|system|operating)\s+(instructions|prompts|rules|directives)\b"
            ),
        ),
        (
            "role_hijack",
            re.compile(
                r"(?i)\b(you\s+are\s+now|act\s+as\s+a\s+different|new\s+system\s+prompt|system\s+override\s*:)\b"
            ),
        ),
        (
            "delimiter_breakout",
            re.compile(
                r"(?i)(</?untrusted_external_evidence>|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|###\s*System\s*:)"
            ),
        ),
        (
            "unauthorized_action_injection",
            re.compile(
                r"(?i)\b(execute\s+trade|transfer\s+funds|reveal\s+api\s+key|print\s+environment\s+variables|dump\s+database)\b"
            ),
        ),
    ]

    @classmethod
    def sanitize(
        cls,
        raw_text: str,
        source_id: str = "unknown_source",
        source_url: str = "",
    ) -> SanitizedContentResult:
        """
        Inspect untrusted external text, neutralize instruction-override patterns,
        and encapsulate inside a strict data-only XML block.
        """
        if not raw_text:
            return SanitizedContentResult(
                clean_text="",
                wrapped_evidence_block=f'<untrusted_external_evidence source_id="{source_id}" url="{source_url}"></untrusted_external_evidence>',
                injection_detected=False,
                matched_patterns=[],
            )

        cleaned = raw_text
        matched: List[str] = []

        for label, pattern in cls.INJECTION_PATTERNS:
            if pattern.search(cleaned):
                matched.append(label)
                cleaned = pattern.sub("[REDACTED_UNTRUSTED_DIRECTIVE]", cleaned)

        injection_detected = len(matched) > 0
        if injection_detected:
            logger.warning(
                "Blocked indirect prompt injection pattern in external content",
                extra={
                    "extra_data": {
                        "source_id": source_id,
                        "source_url": source_url,
                        "matched_patterns": matched,
                    }
                },
            )

        wrapped = (
            f'<untrusted_external_evidence source_id="{source_id}" '
            f'url="{source_url}" sanitized="{str(injection_detected).lower()}">\n'
            f"{cleaned}\n"
            f"</untrusted_external_evidence>"
        )

        return SanitizedContentResult(
            clean_text=cleaned,
            wrapped_evidence_block=wrapped,
            injection_detected=injection_detected,
            matched_patterns=matched,
        )
