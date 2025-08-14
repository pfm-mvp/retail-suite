import os
import logging
from typing import List, Optional, Dict, Any, Tuple, Union
import requests
import pandas as pd

logger = logging.getLogger("pfm.utils")
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        import streamlit as st
        return st.secrets.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return os.getenv(key, default)

API_URL = _get_secret("API_URL", "https://vemcount-agent.onrender.com/get-report")
LIVE_URL = _get_secret("LIVE_URL", "")  # optional

def _flatten_params(params: Dict[str, Union[str, int, float, List, Tuple, None]]) -> List[Tuple[str, str]]:
    flat: List[Tuple[str, str]] = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for item in v:
                if item is None:
                    continue
                flat.append((k, str(item)))
        else:
            flat.append((k, str(v)))
    return flat

def _safe_post(url: str, params_tuples: List[Tuple[str, str]], timeout: int = 30) -> requests.Response:
    logger.info("POST %s", url)
    preview = "&".join([f"{k}={v}" for k, v in params_tuples[:12]])
    if len(params_tuples) > 12:
        preview += f"&...({len(params_tuples)-12} more)"
    logger.info("Body: %s", preview)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=params_tuples, headers=headers, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:800]
        logger.error("HTTP %s: %s | Detail: %s", resp.status_code, e, detail)
        raise
    return resp

def fetch_report(
    *,
    data: List[int],
    data_output: List[str],
    source: str = "shops",
    period: str = "this_month",
    period_step: str = "day",
    company: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    group_by: Optional[str] = None,
    extra: Optional[Dict[str, Union[str, int, float]]] = None
) -> Dict[str, Any]:
    if not API_URL:
        raise RuntimeError("API_URL ontbreekt (zet in .streamlit/secrets.toml).")
    if data and company:
        logger.info("`company` genegeerd omdat `data` is opgegeven.")
    base_params: Dict[str, Union[str, int, float, List, None]] = {
        "source": source,          # 'shops'
        "period": period,
        "period_step": period_step,
        "data": data,
        "data_output": data_output,
    }
    if not data:
        base_params["company"] = company
    if period == "date":
        if not date_from or not date_to:
            raise ValueError("Voor period='date' zijn 'date_from' en 'date_to' verplicht (YYYY-MM-DD).")
        base_params["date_from"] = date_from
        base_params["date_to"] = date_to
    if group_by:
        base_params["group_by"] = group_by
    if extra:
        base_params.update(extra)
    params_tuples = _flatten_params(base_params)
    resp = _safe_post(API_URL, params_tuples)
    return resp.json()

def fetch_live_locations(
    *,
    shop_ids: List[int],
    source: str = "locations",
    extra: Optional[Dict[str, Union[str, int, float]]] = None
) -> Dict[str, Any]:
    if LIVE_URL:
        url = LIVE_URL
    else:
        if not API_URL:
            raise RuntimeError("API_URL ontbreekt voor afleiding LIVE_URL.")
        root = API_URL
        if root.endswith("/get-report"):
            root = root[: -len("/get-report")]
        url = root.rstrip("/") + "/live-inside"   # no '/report'
    base_params: Dict[str, Union[str, int, float, List, None]] = {
        "source": source,   # 'locations'
        "data": shop_ids
    }
    if extra:
        base_params.update(extra)
    params_tuples = _flatten_params(base_params)
    resp = _safe_post(url, params_tuples)
    return resp.json()

def normalize_report_days_to_df(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data_block = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data_block, dict):
        return pd.DataFrame()
    for date_key, shop_map in data_block.items():
        if not isinstance(shop_map, dict):
            continue
        for shop_id, entry in shop_map.items():
            data_dict = entry.get("data", entry) if isinstance(entry, dict) else {}
            row = {"date": date_key, "shop_id": int(shop_id)}
            if isinstance(data_dict, dict):
                row.update({k: v for k, v in data_dict.items()})
            rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["shop_id", "date"]).reset_index(drop=True)
    return df

def normalize_live_to_df(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data_block = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data_block, dict):
        for shop_id, entry in data_block.items():
            row = {"shop_id": int(shop_id)}
            if isinstance(entry, dict):
                row.update(entry)
            rows.append(row)
    elif isinstance(data_block, list):
        for entry in data_block:
            if isinstance(entry, dict):
                rows.append(entry)
    return pd.DataFrame(rows)


def fetch_report_hourly(
    *,
    data: List[int],
    data_output: List[str],
    source: str = "shops",
    period: str = "last_week",
    company: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    group_by: Optional[str] = None,
    extra: Optional[Dict[str, Union[str, int, float]]] = None
) -> Dict[str, Any]:
    """
    Shortcut voor hourly report calls.
    - period_step is altijd 'hour'
    - POST met herhaalde keys zonder []
    - Werkt hetzelfde als fetch_report maar geforceerd naar hourly granulariteit
    """
    if not API_URL:
        raise RuntimeError("API_URL ontbreekt (zet in .streamlit/secrets.toml).")
    if data and company:
        logger.info("`company` genegeerd omdat `data` is opgegeven.")
    base_params: Dict[str, Union[str, int, float, List, None]] = {
        "source": source,
        "period": period,
        "period_step": "hour",
        "data": data,
        "data_output": data_output,
    }
    if not data:
        base_params["company"] = company
    if period == "date":
        if not date_from or not date_to:
            raise ValueError("Voor period='date' zijn 'date_from' en 'date_to' verplicht (YYYY-MM-DD).")
        base_params["date_from"] = date_from
        base_params["date_to"] = date_to
    if group_by:
        base_params["group_by"] = group_by
    if extra:
        base_params.update(extra)
    params_tuples = _flatten_params(base_params)
    resp = _safe_post(API_URL, params_tuples)
    return resp.json()
