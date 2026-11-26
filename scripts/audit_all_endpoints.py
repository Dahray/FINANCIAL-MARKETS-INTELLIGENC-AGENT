"""
Live Parallel External Provider & API Endpoint Health + Payload Verification Audit Script.
Checks every Tier 1, Tier 2, Tier 3, and AI endpoint configured in FMIP concurrently
(completes in ~8 seconds) to detect HTTP 404, 401, 403, 429, SSL, timeout, or parsing issues.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.config import settings
from app.core.ssl_helper import create_http_client

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_preview(text: str, n: int = 120) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:n]


def probe_one(
    group: str,
    label: str,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: float = 10.0,
) -> Tuple[str, str, str]:
    try:
        with create_http_client(timeout=timeout_s, headers=HEADERS, follow_redirects=True) as client:
            if method == "POST":
                r = client.post(url, params=params, json=json_body)
            else:
                r = client.get(url, params=params)
            is_json = r.text.lstrip().startswith(("[", "{"))
            asi_hit = bool(re.search(r"All[- ]Share\s+Index[^0-9]{0,40}([\d,]+\.\d{2})", r.text, re.I))
            fx_hit = bool(re.search(r"(?:NAFEM|NFEM|USD/NGN)[^0-9]{0,25}(1,\d{3}\.\d{2}|\d{4}\.\d{2})", r.text, re.I))
            rss_items = len(re.findall(r"<item>", r.text, re.I))
            flags = []
            if is_json and r.status_code == 200:
                flags.append("JSON_OK")
            if asi_hit:
                flags.append("ASI_PARSED")
            if fx_hit:
                flags.append("FX_PARSED")
            if rss_items:
                flags.append(f"RSS={rss_items}")
            flag_str = ",".join(flags) if flags else "HTML/OTHER"
            line = f"  {label:18s} | HTTP {r.status_code:3d} | len={len(r.text):8d} | {flag_str:14s} | {clean_preview(r.text, 110)}"
            return (group, label, line)
    except Exception as exc:
        return (group, label, f"  {label:18s} | TIMEOUT/ERR | {exc}")


def main() -> None:
    gkey = (settings.GEMINI_API_KEY or "").strip()
    jobs = [
        # 1. CBN Official REST APIs
        ("1_CBN", "CBN_MM_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllMoneyMarketIndicators", None, None, 15.0),
        ("1_CBN", "CBN_INF_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllInflationRates", None, None, 15.0),
        ("1_CBN", "CBN_NFEM_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllNFEM_Rates", None, None, 15.0),
        ("1_CBN", "CBN_RES_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllReserves", None, None, 15.0),
        ("1_CBN", "CBN_OIL_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllCrudeOilPrices", None, None, 15.0),
        ("1_CBN", "CBN_NTB_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllSecuritiesNTB", None, None, 15.0),
        ("1_CBN", "CBN_CIRC_API", "GET", f"{settings.CBN_BASE_URL}/api/GetAllCirculars", None, None, 15.0),
        # 2. Other Nigerian Official Sources
        ("2_NG_OFFICIAL", "NGX_HOME", "GET", settings.NGX_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "NGX_INDICES", "GET", "https://ngxgroup.com/exchange/data/indices/", None, None, 10.0),
        ("2_NG_OFFICIAL", "FMDQ_HOME", "GET", settings.FMDQ_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "DMO_HOME", "GET", settings.DMO_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "NBS_HOME", "GET", settings.NBS_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "SEC_NIGERIA", "GET", settings.SEC_NIGERIA_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "PENCOM", "GET", settings.PENCOM_BASE_URL, None, None, 10.0),
        ("2_NG_OFFICIAL", "NAICOM", "GET", settings.NAICOM_BASE_URL, None, None, 10.0),
        # 3. Global & Paid/Free Market APIs
        ("3_GLOBAL_API", "FMP_STABLE_SPX", "GET", "https://financialmodelingprep.com/stable/quote", {"symbol": "^GSPC", "apikey": settings.FMP_API_KEY}, None, 12.0),
        ("3_GLOBAL_API", "FMP_STABLE_NDX", "GET", "https://financialmodelingprep.com/stable/quote", {"symbol": "^IXIC", "apikey": settings.FMP_API_KEY}, None, 12.0),
        ("3_GLOBAL_API", "FMP_STABLE_GOLD", "GET", "https://financialmodelingprep.com/stable/quote", {"symbol": "GCUSD", "apikey": settings.FMP_API_KEY}, None, 12.0),
        ("3_GLOBAL_API", "ALPHA_VANTAGE", "GET", "https://www.alphavantage.co/query", {"function": "CURRENCY_EXCHANGE_RATE", "from_currency": "USD", "to_currency": "NGN", "apikey": settings.ALPHA_VANTAGE_API_KEY}, None, 12.0),
        ("3_GLOBAL_API", "FRED_DGS10", "GET", "https://api.stlouisfed.org/fred/series/observations", {"series_id": "DGS10", "api_key": settings.FRED_API_KEY, "file_type": "json", "sort_order": "desc", "limit": 1}, None, 12.0),
        ("3_GLOBAL_API", "FRED_BRENT", "GET", "https://api.stlouisfed.org/fred/series/observations", {"series_id": "DCOILBRENTEU", "api_key": settings.FRED_API_KEY, "file_type": "json", "sort_order": "desc", "limit": 1}, None, 12.0),
        ("3_GLOBAL_API", "FRED_FEDFUNDS", "GET", "https://api.stlouisfed.org/fred/series/observations", {"series_id": "FEDFUNDS", "api_key": settings.FRED_API_KEY, "file_type": "json", "sort_order": "desc", "limit": 1}, None, 12.0),
        ("3_GLOBAL_API", "WORLD_BANK_GDP", "GET", "https://api.worldbank.org/v2/country/NGA/indicator/NY.GDP.MKTP.KD.ZG", {"format": "json", "per_page": 3}, None, 12.0),
        # 4. Press & Search
        ("4_PRESS_SEARCH", "NAIRAMETRICS_RSS", "GET", "https://nairametrics.com/feed/", None, None, 12.0),
        ("4_PRESS_SEARCH", "BUSINESSDAY_RSS", "GET", "https://businessday.ng/feed/", None, None, 12.0),
        ("4_PRESS_SEARCH", "TAVILY_SEARCH", "POST", "https://api.tavily.com/search", None, {"api_key": settings.TAVILY_API_KEY, "query": "NGX All Share Index Nigeria market today", "max_results": 2}, 12.0),
        # 5. Gemini AI (Verified Active Models)
        ("5_GEMINI_AI", "GEMINI_PRIMARY", "POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent", {"key": gkey}, {"contents": [{"parts": [{"text": "Reply OK"}]}], "generationConfig": {"maxOutputTokens": 256}}, 25.0),
        ("5_GEMINI_AI", "GEMINI_FAST", "POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent", {"key": gkey}, {"contents": [{"parts": [{"text": "Reply OK"}]}], "generationConfig": {"maxOutputTokens": 256}}, 25.0),
        ("5_GEMINI_AI", "GEMINI_EMBED_768", "POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent", {"key": gkey}, {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": "CBN Monetary Policy Rate"}]}, "outputDimensionality": 768}, 15.0),
    ]

    results: List[Tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(probe_one, *j) for j in jobs]
        for fut in as_completed(futs):
            results.append(fut.result())

    results.sort(key=lambda x: (x[0], x[1]))
    curr_group = ""
    for grp, _, line in results:
        if grp != curr_group:
            print(f"\n=== {grp} ===")
            curr_group = grp
        print(line)
    print(f"\nGEMINI_KEY_PREFIX: '{gkey[:8]}...' (len={len(gkey)})")


if __name__ == "__main__":
    main()
