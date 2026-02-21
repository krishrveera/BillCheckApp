"""
CMS Medicare Fee Schedule API Client

Fetches real Medicare payment data from the CMS.gov public API:
  Medicare Physician & Other Practitioners — by Geography and Service

Dataset: https://data.cms.gov/provider-summary-by-type-of-service/
         medicare-physician-other-practitioners/
         medicare-physician-other-practitioners-by-geography-and-service

The dataset is updated annually by CMS.  We query for national-level
average Medicare payment amounts per HCPCS / CPT code.

Falls back to the static CMS_FEE_SCHEDULE in reference_data.py when
the API is unreachable or a code is missing from the dataset.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

# ── CMS Data API configuration ──────────────────────────────────────────────
# UUID for "Medicare Physician & Other Practitioners - by Geography and Service"
_CMS_DATASET_UUID = "6fea9d79-0129-4e4c-b1b8-23cd86a4f435"
_CMS_API_BASE = (
    f"https://data.cms.gov/data-api/v1/dataset/{_CMS_DATASET_UUID}/data"
)

# ── Cache configuration ─────────────────────────────────────────────────────
_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
_CACHE_FILE = _CACHE_DIR / "cms_rates.json"
_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days — data updates annually anyway

# ── HTTP settings ────────────────────────────────────────────────────────────
_HTTP_TIMEOUT = 15  # seconds per request


# ---------------------------------------------------------------------------
# Internal cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    """Load the on-disk cache.  Returns {} if missing or expired."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        raw = json.loads(_CACHE_FILE.read_text())
        ts = raw.get("_timestamp", 0)
        if time.time() - ts > _CACHE_TTL_SECONDS:
            return {}
        return raw.get("rates", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_cache(rates: dict) -> None:
    """Persist rates dict to disk."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"_timestamp": time.time(), "rates": rates}
    _CACHE_FILE.write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# CMS API query
# ---------------------------------------------------------------------------

def _fetch_code_from_cms(hcpcs_code: str, client: httpx.Client) -> Optional[dict]:
    """
    Query the CMS data API for a single HCPCS/CPT code.

    Returns a dict with:
        {
            "description": str,
            "avg_medicare_payment": float,   # national avg Medicare payment
            "avg_medicare_allowed": float,   # national avg Medicare allowed
            "avg_submitted_charge": float,   # national avg submitted charge
            "place_of_service": str,         # "F" (facility) or "O" (office)
        }
    or None if the code is not found.

    When both Facility and Office rows exist we prefer Facility (hospital
    bills are the primary use-case of BillCheck).
    """
    url = f"{_CMS_API_BASE}?filter[HCPCS_Cd]={hcpcs_code}&size=100"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            return None

        # Keep only national-level rows
        national = [
            r for r in rows if r.get("Rndrng_Prvdr_Geo_Lvl") == "National"
        ]
        if not national:
            return None

        # Prefer Facility row, then Office, then whatever is available
        def _pick_row(rows_list):
            for pref in ("F", "O"):
                for r in rows_list:
                    if r.get("Place_Of_Srvc") == pref:
                        return r
            return rows_list[0]

        row = _pick_row(national)
        return {
            "description": row.get("HCPCS_Desc", ""),
            "avg_medicare_payment": float(row.get("Avg_Mdcr_Pymt_Amt", 0)),
            "avg_medicare_allowed": float(row.get("Avg_Mdcr_Alowd_Amt", 0)),
            "avg_submitted_charge": float(row.get("Avg_Sbmtd_Chrg", 0)),
            "place_of_service": row.get("Place_Of_Srvc", ""),
        }
    except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError):
        return None


def fetch_rates(
    hcpcs_codes: list[str],
    *,
    use_cache: bool = True,
) -> dict[str, dict]:
    """
    Fetch Medicare payment data for a list of HCPCS / CPT codes.

    Returns a dict keyed by HCPCS code.  Each value is the dict returned by
    ``_fetch_code_from_cms`` (or cached equivalent).  Codes that could not
    be resolved are omitted from the result.

    Parameters
    ----------
    hcpcs_codes : list[str]
        The codes to look up (e.g. ``["99213", "80053"]``).
    use_cache : bool
        If True (default) use / populate the disk cache.
    """
    cached = _load_cache() if use_cache else {}
    result: dict[str, dict] = {}
    codes_to_fetch: list[str] = []

    for code in hcpcs_codes:
        if code in cached:
            result[code] = cached[code]
        else:
            codes_to_fetch.append(code)

    if codes_to_fetch:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            for code in codes_to_fetch:
                data = _fetch_code_from_cms(code, client)
                if data is not None:
                    result[code] = data
                    cached[code] = data

        if use_cache and cached:
            _save_cache(cached)

    return result


def get_medicare_rate(
    hcpcs_code: str,
    *,
    use_cache: bool = True,
) -> Optional[float]:
    """
    Convenience: return the national average Medicare payment for one code,
    or None if unavailable.
    """
    rates = fetch_rates([hcpcs_code], use_cache=use_cache)
    entry = rates.get(hcpcs_code)
    if entry is None:
        return None
    return entry["avg_medicare_payment"]


# ---------------------------------------------------------------------------
# Build a full fee schedule dict compatible with the existing
# ``CMS_FEE_SCHEDULE`` structure in reference_data.py
# ---------------------------------------------------------------------------

def build_fee_schedule(
    hcpcs_codes: list[str],
    fallback: dict | None = None,
    *,
    use_cache: bool = True,
) -> dict[str, dict]:
    """
    Build a fee schedule dict in the same shape as ``CMS_FEE_SCHEDULE``.

    Keys   : HCPCS code strings
    Values : ``{"description": str, "medicare_rate": float, "category": str}``

    ``medicare_rate`` is set to the **avg_medicare_allowed** amount from CMS
    (the Medicare allowed amount is the closest analogue to the fee schedule
    rate — it includes the provider payment *plus* patient cost-sharing).

    For any code not found via the API, the ``fallback`` dict (existing
    hardcoded data) is used.
    """
    api_data = fetch_rates(hcpcs_codes, use_cache=use_cache)
    fallback = fallback or {}
    schedule: dict[str, dict] = {}

    for code in hcpcs_codes:
        if code in api_data:
            entry = api_data[code]
            # Guard against incomplete cache entries
            if "avg_medicare_allowed" in entry:
                schedule[code] = {
                    "description": entry.get("description", ""),
                    "medicare_rate": entry["avg_medicare_allowed"],
                    "category": _guess_category(code),
                    "source": "cms_api",
                    "avg_submitted_charge": entry.get("avg_submitted_charge", 0.0),
                }
            elif code in fallback:
                schedule[code] = {**fallback[code], "source": "fallback"}
        elif code in fallback:
            fb = fallback[code]
            schedule[code] = {
                **fb,
                "source": "fallback",
            }
        # else: code not available anywhere — skip

    return schedule


def _guess_category(code: str) -> str:
    """Rough category guess from the code prefix."""
    if code.startswith("99"):
        return "E&M"
    if code.startswith("8"):
        return "Lab"
    if code.startswith("7"):
        return "Radiology"
    if code.startswith("93") or code.startswith("33"):
        return "Cardiac"
    if code.startswith("9636") or code.startswith("9637"):
        return "IV/Infusion"
    if code.startswith("J"):
        return "Pharmacy"
    if code.startswith("88"):
        return "Pathology"
    if code.startswith("97"):
        return "PT"
    if code.startswith("94"):
        return "Respiratory"
    if code.startswith("00") or code.startswith("01"):
        return "Anesthesia"
    if code.startswith("2") or code.startswith("4"):
        return "Surgery"
    return "Other"
