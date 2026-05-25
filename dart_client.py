import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
_API_KEY = os.getenv("DART_API_KEY")


def _get_dart():
    import dart_fss as dart
    dart.set_api_key(_API_KEY)
    return dart


def search_company(name: str) -> list[dict]:
    """기업명으로 DART 등록 기업 검색 (최대 5건)"""
    try:
        dart = _get_dart()
        corp_list = dart.get_corp_list()
        results = corp_list.find_by_corp_name(name, exactly=False)
        return [
            {
                "corp_name": c.corp_name,
                "corp_code": c.corp_code,
                "stock_code": getattr(c, "stock_code", ""),
            }
            for c in results[:5]
        ]
    except Exception:
        return []


def get_financials(corp_code: str, years: list[int] = None) -> pd.DataFrame:
    """DART에서 연도별 손익계산서 핵심 지표 조회"""
    if years is None:
        years = [2022, 2023, 2024]

    rows = []
    try:
        dart = _get_dart()
        corp_list = dart.get_corp_list()
        corp = corp_list.find_by_corp_code(corp_code)

        for year in years:
            try:
                fs = corp.extract_fs(bgn_de=f"{year}0101")
                is_df = fs.get("is", pd.DataFrame())
                if is_df.empty:
                    continue

                def get_val(keyword: str):
                    mask = is_df["label_ko"].str.contains(keyword, na=False)
                    hit = is_df[mask]
                    if hit.empty:
                        return None
                    raw = str(hit.iloc[0].get("thstrm_amount", "")).replace(",", "").strip()
                    return int(raw) if raw.lstrip("-").isdigit() else None

                rows.append({
                    "연도": year,
                    "매출액": get_val("매출액"),
                    "영업이익": get_val("영업이익"),
                    "당기순이익": get_val("당기순이익"),
                })
            except Exception:
                continue
    except Exception:
        pass

    return pd.DataFrame(rows)
