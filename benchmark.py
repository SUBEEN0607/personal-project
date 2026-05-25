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


def _ecos_fetch_monthly(stat_code: str, item_code: str, start: str, end: str) -> pd.DataFrame:
    """월별 데이터 조회 (cycle=M)"""
    url = f"{_ECOS_BASE}/{_ECOS_KEY}/json/kr/1/500/{stat_code}/M/{start}/{end}/{item_code}"
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


def _ecos_fetch_daily_to_monthly(stat_code: str, item_code: str, start: str, end: str) -> pd.DataFrame:
    """일별 데이터 조회 후 월말 기준으로 resample"""
    url = f"{_ECOS_BASE}/{_ECOS_KEY}/json/kr/1/2000/{stat_code}/D/{start}/{end}/{item_code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json().get("StatisticSearch", {})
        rows = data.get("row", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]].copy()
        df.columns = ["날짜", "값"]
        df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d")
        df["값"] = pd.to_numeric(df["값"], errors="coerce")
        # 월별 평균으로 집계
        monthly = df.set_index("날짜").resample("ME")["값"].mean().reset_index()
        monthly.columns = ["기간", "값"]
        monthly["기간"] = monthly["기간"].dt.strftime("%Y%m")
        return monthly.dropna()
    except Exception:
        return pd.DataFrame()


def get_base_rate(months: int = 24) -> pd.DataFrame:
    """한국은행 기준금리 (최근 N개월, 2026년 최신까지)"""
    today = pd.Timestamp.today()
    end = today.strftime("%Y%m")
    start = (today - pd.DateOffset(months=months)).strftime("%Y%m")
    df = _ecos_fetch_monthly("722Y001", "0101000", start, end)
    if not df.empty:
        df.rename(columns={"값": "기준금리(%)"}, inplace=True)
    return df


def get_exchange_rate(months: int = 24) -> pd.DataFrame:
    """원/달러 환율 월평균 (최근 N개월, 2026년 최신까지 — 일별→월별 resample)"""
    today = pd.Timestamp.today()
    end = today.strftime("%Y%m%d")
    start = (today - pd.DateOffset(months=months)).strftime("%Y%m%d")
    df = _ecos_fetch_daily_to_monthly("731Y001", "0000001", start, end)
    if not df.empty:
        df.rename(columns={"값": "원/달러(원)"}, inplace=True)
    return df


_kvic_cache: pd.DataFrame = pd.DataFrame()


def _get_kvic_all() -> pd.DataFrame:
    """전체 KVIC 펀드 데이터 1회 호출 후 캐시 (API가 연도 필터 미지원)"""
    global _kvic_cache
    if not _kvic_cache.empty:
        return _kvic_cache
    if not _KVIC_KEY:
        return pd.DataFrame()
    try:
        r = requests.get(f"{_KVIC_BASE}/fundType", params={"key": _KVIC_KEY, "fundType": "00"}, timeout=15)
        data = r.json()
        all_rows = []
        for k, v in data.items():
            if k.startswith("result") and isinstance(v, list):
                all_rows.extend(v)
        if not all_rows:
            return pd.DataFrame()
        df = pd.DataFrame(all_rows)
        df["amt"] = pd.to_numeric(df["amt"], errors="coerce")
        # "2023년" → "2023" (한글 년 제거, 비ASCII 포함 대응)
        df["year"] = df["year"].str.extract(r"(\d{4})")
        df.rename(columns={
            "year": "결성연도", "fd": "투자분야", "mng": "운용사",
            "asn": "조합명", "exp": "만기일", "amt": "약정액(백만원)"
        }, inplace=True)
        _kvic_cache = df
        return df
    except Exception:
        return pd.DataFrame()


def get_kvic_funds(year: int = None) -> pd.DataFrame:
    """연도별 필터링된 펀드 목록 (year=None이면 전체)"""
    df = _get_kvic_all()
    if df.empty:
        return df
    if year:
        df = df[df["결성연도"] == str(year)]
    return df.reset_index(drop=True)


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


def get_kvic_yearly_trend() -> pd.DataFrame:
    """연도별 결성 조합 수 + 총 약정액 추이 (전체 연도, API 1회 호출)"""
    df = _get_kvic_all()
    if df.empty:
        return pd.DataFrame()
    trend = (
        df.groupby("결성연도")
        .agg(결성조합수=("조합명", "count"), 총약정액=("약정액(백만원)", "sum"))
        .reset_index()
        .sort_values("결성연도")
    )
    trend["총약정액(억원)"] = (trend["총약정액"] / 100).round(0).astype(int)
    return trend.drop(columns=["총약정액"])


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
