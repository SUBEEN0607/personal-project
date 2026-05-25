import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_ECOS_KEY = os.getenv("ECOS_API_KEY")
_MSME_KEY = os.getenv("MSME_API_KEY")  # data.go.kr에서 발급 필요
_ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"


def _ecos_fetch(stat_code: str, item_code: str, start: str, end: str, cycle: str = "MM") -> pd.DataFrame:
    url = f"{_ECOS_BASE}/{_ECOS_KEY}/json/kr/1/100/{stat_code}/{cycle}/{start}/{end}/{item_code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json().get("StatisticSearch", {})
        rows = data.get("row", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]].copy()
        df.columns = ["기간", "값"]
        df["값"] = pd.to_numeric(df["값"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def get_base_rate(months: int = 24) -> pd.DataFrame:
    """한국은행 기준금리 (최근 N개월)"""
    end = pd.Timestamp.today().strftime("%Y%m")
    start = (pd.Timestamp.today() - pd.DateOffset(months=months)).strftime("%Y%m")
    df = _ecos_fetch("722Y001", "0101000", start, end, "MM")
    if not df.empty:
        df.rename(columns={"값": "기준금리(%)"}, inplace=True)
    return df


def get_exchange_rate(months: int = 24) -> pd.DataFrame:
    """원/달러 환율 월평균 (최근 N개월)"""
    end = pd.Timestamp.today().strftime("%Y%m")
    start = (pd.Timestamp.today() - pd.DateOffset(months=months)).strftime("%Y%m")
    df = _ecos_fetch("731Y001", "0000001", start, end, "MM")
    if not df.empty:
        df.rename(columns={"값": "원/달러(원)"}, inplace=True)
    return df


def get_vc_trend() -> pd.DataFrame:
    """국내 VC 벤처투자 분기별 집계 (중소벤처기업부 data.go.kr)
    MSME_API_KEY 필요: data.go.kr → '벤처투자 정보 서비스' 검색 후 활용신청
    """
    if not _MSME_KEY:
        return pd.DataFrame()

    url = (
        "https://apis.data.go.kr/B552735/ventureinvest/getVentureInvestList"
        f"?serviceKey={_MSME_KEY}&pageNo=1&numOfRows=20&resultType=json"
    )
    try:
        res = requests.get(url, timeout=10)
        items = res.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            return pd.DataFrame()
        return pd.DataFrame(items)
    except Exception:
        return pd.DataFrame()
