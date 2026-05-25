import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_ECOS_KEY = os.getenv("ECOS_API_KEY")
_MSME_KEY = os.getenv("MSME_API_KEY")
_KVIC_KEY = os.getenv("KVIC_API_KEY")
_ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"
_KVIC_BASE = "https://www.kvic.or.kr/api"


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


def get_kvic_fund_types() -> list[dict]:
    """한국벤처투자 모태펀드 종류 목록"""
    if not _KVIC_KEY:
        return []
    try:
        r = requests.get(f"{_KVIC_BASE}/businessType", params={"key": _KVIC_KEY, "bType": "0"}, timeout=10)
        return r.json().get("result", [])
    except Exception:
        return []


def get_kvic_funds(year: int = None) -> pd.DataFrame:
    """한국벤처투자 펀드 현황 조회
    year: 결성연도 (None이면 최신 기본값)
    반환: year, fd(분야), mng(운용사), asn(조합명), exp(만기일), amt(금액백만원)
    """
    if not _KVIC_KEY:
        return pd.DataFrame()
    params = {"key": _KVIC_KEY, "fundType": "00"}
    if year:
        params["y"] = str(year)
    try:
        r = requests.get(f"{_KVIC_BASE}/fundType", params=params, timeout=15)
        data = r.json()
        all_rows = []
        for k, v in data.items():
            if k.startswith("result") and isinstance(v, list):
                all_rows.extend(v)
        if not all_rows:
            return pd.DataFrame()
        df = pd.DataFrame(all_rows)
        df["amt"] = pd.to_numeric(df["amt"], errors="coerce")
        df["year"] = df["year"].str.replace("년", "", regex=False).str.strip()
        df.rename(columns={
            "year": "결성연도", "fd": "투자분야", "mng": "운용사",
            "asn": "조합명", "exp": "만기일", "amt": "약정액(백만원)"
        }, inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def get_kvic_sector_summary(year: int = None) -> pd.DataFrame:
    """분야별 조합 수 + 총 약정액 집계 (벤치마크용)"""
    df = get_kvic_funds(year)
    if df.empty:
        return pd.DataFrame()
    summary = (
        df.groupby("투자분야")
        .agg(조합수=("조합명", "count"), 총약정액=("약정액(백만원)", "sum"))
        .reset_index()
        .sort_values("총약정액", ascending=False)
    )
    summary["총약정액(억원)"] = (summary["총약정액"] / 100).round(0).astype(int)
    return summary.drop(columns=["총약정액"])


def get_kvic_yearly_trend(years: list = None) -> pd.DataFrame:
    """연도별 결성 조합 수 + 총 약정액 추이"""
    if years is None:
        years = list(range(2019, pd.Timestamp.today().year + 1))
    rows = []
    for y in years:
        df = get_kvic_funds(y)
        if not df.empty:
            rows.append({
                "연도": str(y),
                "결성조합수": len(df),
                "총약정액(억원)": int(df["약정액(백만원)"].sum() / 100),
            })
    return pd.DataFrame(rows)


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
