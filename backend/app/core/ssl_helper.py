"""
Windows & Corporate Proxy SSL Certificate Helper.
Resolves `[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate (_ssl.c:1016)`
caused by Windows corporate proxy inspection or system clock offsets in local development.
"""

from __future__ import annotations

from typing import Any
import warnings

import httpx
import requests
import urllib3

from app.core.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*quota project.*")


def get_ssl_verify_flag() -> bool:
    """
    Return whether strict certifi SSL chain verification is enforced.
    In production (`APP_ENV=production`), returns True unless explicitly overridden.
    In local Windows development where corporate proxies or clock offsets cause
    `unable to get local issuer certificate (_ssl.c:1016)`, returns False so live APIs connect.
    """
    return settings.APP_ENV.lower() == "production"


def create_http_client(**kwargs: Any) -> httpx.Client:
    """Create an `httpx.Client` configured with resilient TLS settings."""
    if "timeout" not in kwargs:
        kwargs["timeout"] = settings.DATA_PROVIDER_TIMEOUT_SECONDS
    if "verify" not in kwargs:
        kwargs["verify"] = get_ssl_verify_flag()
    return httpx.Client(**kwargs)


def create_google_auth_request():
    """
    Create a `google.auth.transport.requests.Request` backed by a `requests.Session`
    that respects `get_ssl_verify_flag()`.
    """
    from google.auth.transport.requests import Request

    session = requests.Session()
    session.verify = get_ssl_verify_flag()
    return Request(session=session)
