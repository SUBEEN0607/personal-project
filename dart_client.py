import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
_API_KEY = os.getenv("DART_API_KEY")
_DART_BASE = "https://opendart.fss.or.kr/api"


def search_company(name: str) -> list[dict]:
    """기업명으로 DART 등록 기업 검색 (상장사 우선, 최대 5건)"""
    try:
        import dart_fss as dart
        dart.set_api_key(_API_KEY)
        corp_list = dart.get_corp_list()
        # 정확 일치 먼저, 없으면 부분 일치
        results = corp_list.find_by_corp_name(name, exactly=True)
        if not results:
            results = corp_list.find_by_corp_name(name, exactly=False)
        # 상장사(stock_code 있는 것) 우선 정렬
        results = sorted(results, key=lambda c: (0 if getattr(c, "stock_code", "") else 1))
        return [
            {
                "corp_name": c.corp_name,
                "corp_code": c.corp_code,
                "stock_code": getattr(c, "stock_code", "") or "",
            }
            for c in results[:5]
        ]
    except Exception:
        return []


def get_financials(corp_code: str, years: list[int] = None) -> pd.DataFrame:
    """DART OpenAPI 직접 호출로 연도별 손익계산서 조회 (빠르고 안정적)
    reprt_code 11011=사업보고서(연간)
    """
    if years is None:
        years = [2022, 2023, 2024]

    rows = []
    for year in years:
        try:
            r = requests.get(
                f"{_DART_BASE}/fnlttSinglAcnt.json",
                params={
                    "crtfc_key": _API_KEY,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": "11011",  # 사업보고서
                },
                timeout=10,
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

    return pd.DataFrame(rows)
