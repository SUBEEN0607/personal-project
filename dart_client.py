import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def _load_api_key() -> str | None:
    key = os.getenv("DART_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("DART_API_KEY") or st.secrets.get("dart_api_key")
        except Exception:
            pass
    return key

_API_KEY = _load_api_key()
_DART_BASE = "https://opendart.fss.or.kr/api"

_corp_list_cache = None
_search_cache: dict[str, list] = {}
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dart_search_cache.json")


def _load_disk_cache():
    global _search_cache
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                _search_cache = json.load(f)
    except Exception:
        _search_cache = {}

def _save_disk_cache():
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_search_cache, f, ensure_ascii=False)
    except Exception:
        pass

_load_disk_cache()


def _get_corp_list():
    global _corp_list_cache, _API_KEY
    if _corp_list_cache is None:
        if not _API_KEY:
            _API_KEY = _load_api_key()
        import dart_fss as dart
        dart.set_api_key(_API_KEY)
        _corp_list_cache = dart.get_corp_list()
    return _corp_list_cache


def search_company(name: str) -> list[dict]:
    """기업명으로 DART 등록 기업 검색 (디스크 캐시 활용)"""
    if name in _search_cache:
        return _search_cache[name]

    try:
        corp_list = _get_corp_list()
        results = corp_list.find_by_corp_name(name, exactly=True)
        if not results:
            results = corp_list.find_by_corp_name(name, exactly=False)
        results = sorted(results, key=lambda c: (0 if getattr(c, "stock_code", "") else 1))
        found = [
            {
                "corp_name": c.corp_name,
                "corp_code": c.corp_code,
                "stock_code": getattr(c, "stock_code", "") or "",
            }
            for c in results[:5]
        ]
        _search_cache[name] = found
        _save_disk_cache()
        return found
    except Exception:
        _search_cache[name] = []
        _save_disk_cache()
        return []


_fin_cache: dict[str, pd.DataFrame] = {}

def get_financials(corp_code: str, years: list[int] = None) -> pd.DataFrame:
    """DART OpenAPI 직접 호출로 연도별 손익계산서 조회 (캐시 적용)"""
    global _API_KEY
    if not _API_KEY:
        _API_KEY = _load_api_key()
    if not _API_KEY:
        return pd.DataFrame()
    if years is None:
        years = [2022, 2023, 2024]

    cache_key = f"{corp_code}_{'_'.join(map(str, years))}"
    if cache_key in _fin_cache:
        return _fin_cache[cache_key]

    rows = []
    for year in years:
        try:
            r = requests.get(
                f"{_DART_BASE}/fnlttSinglAcnt.json",
                params={
                    "crtfc_key": _API_KEY,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": "11011",
                },
                timeout=5,
            )
            data = r.json()
            if data.get("status") != "000":
                continue

            items = {row["account_nm"]: row for row in data.get("list", [])}

            def get_val(keywords: list[str]) -> int | None:
                for kw in keywords:
                    for nm, row in items.items():
                        if kw in nm:
                            raw = row.get("thstrm_amount", "").replace(",", "").strip()
                            if raw.lstrip("-").isdigit():
                                return int(raw)
                return None

            revenue = get_val(["매출액", "수익(매출액)", "영업수익"])
            op_income = get_val(["영업이익"])
            net_income = get_val(["당기순이익"])

            if any(v is not None for v in [revenue, op_income, net_income]):
                rows.append({
                    "연도": year,
                    "매출액": revenue,
                    "영업이익": op_income,
                    "당기순이익": net_income,
                })
        except Exception:
            continue

    result = pd.DataFrame(rows)
    _fin_cache[cache_key] = result
    return result
