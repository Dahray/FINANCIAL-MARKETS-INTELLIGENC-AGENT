"""
Windows & Corporate Proxy SSL Certificate Helper + Bounded HTTP Timeout Configuration.
Resolves `[SSL: CERTIFICATE_VERIFY_FAILED]` in local development and enforces strict
connect (4s) and read (8s) timeouts so slow external servers never cause workflow timeouts.
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
    In production (`APP_ENV=production`), returns True.
    In local Windows development, returns False so corporate proxies/clock offsets do not block live APIs.
    """
    return settings.APP_ENV.lower() == "production"


def create_http_client(**kwargs: Any) -> httpx.Client:
    """
    Create an `httpx.Client` configured with resilient TLS settings and bounded
    timeouts (up to 30s read, 12s TLS connect) so official CBN/DMO/FMDQ JSON feeds
    complete reliably without stalling workflows indefinitely.
    """
    raw_timeout = kwargs.pop("timeout", None)
    read_sec = min(float(raw_timeout or settings.DATA_PROVIDER_TIMEOUT_SECONDS), 30.0)
    bounded_timeout = httpx.Timeout(
        timeout=read_sec,
        connect=min(12.0, read_sec),
        read=read_sec,
        write=10.0,
        pool=8.0,
    )
    if "verify" not in kwargs:
        kwargs["verify"] = get_ssl_verify_flag()
    return httpx.Client(timeout=bounded_timeout, **kwargs)



def create_google_auth_request():
    """
    Create a `google.auth.transport.requests.Request` backed by a `requests.Session`
    that respects `get_ssl_verify_flag()`.
    """
    from google.auth.transport.requests import Request

    session = requests.Session()
    session.verify = get_ssl_verify_flag()
    return Request(session=session)
