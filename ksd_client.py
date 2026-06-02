"""
한국예탁결제원(KSD) 오픈API 클라이언트
https://openapi.ksd.or.kr

사전 준비:
  1. https://openapi.ksd.or.kr 회원가입 후 API 키 발급
  2. .env 에 KSD_API_KEY=발급키 추가

공통 응답 구조:
  {"resultCode": "00", "result": {"xxList": [...]}}
  resultCode "00" = 정상, 그 외 = 오류
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_KEY  = os.getenv("KSD_API_KEY")
_BASE = "https://openapi.ksd.or.kr/api/dostk"

# API ID → URL 경로 매핑
_PATH_MAP: dict[str, str] = {
    # 공통정보 (cmn)
    "getIssucoCustnoByIsin":   "cmn",
    "getStddtInfo":            "cmn",
    "getGmeetInfo":            "cmn",
    "getGmeetMeasureInfo":     "cmn",
    "getFmnmAltInfo":          "cmn",
    "getCostPaySchedul":       "cmn",
    "getDivSchedulInfo":       "cmn",
    "getDivInfo":              "cmn",
    "getOddLotInfo":           "cmn",
    # 주식정보 (stk)
    "getStkStatInfo":          "stk",
    "getUnlistCirclInfo":      "stk",
    "getSlbDealingByIsin":     "stk",
    "getShotnByMart":          "stk",
    "getStkListInfo":          "stk",
    "getXrcStkStatInfo":       "stk",
    "getXrcStkOptionXrcInfo":  "stk",
    "getStkIncdecDetails":     "stk",
    "getSafeDpDutyDepoStatus": "stk",
    # 채권정보 (bnd)
    "getBondIssuInfo":         "bnd",
    "getBondStatInfo":         "bnd",
    "getIntPayInfo":           "bnd",
    "getBondOptionXrcInfo":    "bnd",
    "getShortmIssuInfo":       "bnd",
    "getCDInfo":               "bnd",
    "getCPInfo":               "bnd",
    "getESTBInfo":             "bnd",
    # 파생결합증권정보 (drv)
    "getDerivCombiIssuInfo":   "drv",
    "getBassetUnredScale":     "drv",
    "getDerivCombiIsinInfo":   "drv",
    "getAssetInfo":            "drv",
    "getAssetXrcInfo":         "drv",
    "getRedCondiInfo":         "drv",
    "getRedIsinInfo":          "drv",
    # 외화증권정보 (frs)
    "getNationFrsecCusInfo":   "frs",
    "getNationFrsecSetlInfo":  "frs",
    "getSecnFrsecCusInfo":     "frs",
    "getSecnFrsecSetlInfo":    "frs",
}


# ── 내부 공통 요청 핸들러 ──────────────────────────────────────────

def _fetch(api_id: str, params: dict, rows: int = 200) -> list[dict]:
    """KSD API 호출 → row 리스트 반환 (오류 시 빈 리스트)"""
    if not _KEY:
        raise EnvironmentError("KSD_API_KEY가 .env에 없습니다.")
    path = _PATH_MAP.get(api_id)
    if not path:
        raise ValueError(f"알 수 없는 API ID: {api_id}")
    url = f"{_BASE}/{path}"
    p = {
        "serviceKey": _KEY,
        "pageNo":     1,
        "numOfRows":  rows,
        "apiId":      api_id,
        **params,
    }
    try:
        r = requests.get(url, params=p, timeout=15)
        r.raise_for_status()
        body = r.json()
        if body.get("resultCode") not in ("00", "000"):
            return []
        result = body.get("result", {})
        for v in result.values():
            if isinstance(v, list):
                return v
        return []
    except Exception:
        return []


def _df(api_id: str, params: dict, rows: int = 200) -> pd.DataFrame:
    """_fetch 결과를 DataFrame으로 변환"""
    data = _fetch(api_id, params, rows)
    return pd.DataFrame(data) if data else pd.DataFrame()


# ── 범용 호출 (직접 사용 가능) ────────────────────────────────────

def call(api_id: str, **params) -> pd.DataFrame:
    """
    임의 API 직접 호출.
    예) ksd_client.call("getDivInfo", isin="KR7005930003", basDt="20240101")
    """
    return _df(api_id, params)


# ── 공통정보 ──────────────────────────────────────────────────────

def get_issuer_by_isin(isin: str) -> pd.DataFrame:
    """발행종목(ISIN)으로 발행회사번호 조회"""
    return _df("getIssucoCustnoByIsin", {"isin": isin})


def get_record_date(isin: str, year: str = "") -> pd.DataFrame:
    """기준일 정보 (isin + 연도 4자리, 예: '2024')"""
    p = {"isin": isin}
    if year:
        p["stddtY"] = year
    return _df("getStddtInfo", p)


def get_gm_schedule(isin: str = "", year: str = "") -> pd.DataFrame:
    """총회일정 정보"""
    p: dict = {}
    if isin:  p["isin"]    = isin
    if year:  p["gmeetY"]  = year
    return _df("getGmeetInfo", p)


def get_gm_agenda(isin: str, gm_date: str = "") -> pd.DataFrame:
    """총회안건 정보 (gm_date: YYYYMMDD)"""
    p = {"isin": isin}
    if gm_date:
        p["gmeetDt"] = gm_date
    return _df("getGmeetMeasureInfo", p)


def get_name_change(isin: str = "") -> pd.DataFrame:
    """상호변경 정보"""
    p = {"isin": isin} if isin else {}
    return _df("getFmnmAltInfo", p)


def get_payment_schedule(isin: str) -> pd.DataFrame:
    """대금지급일정 정보"""
    return _df("getCostPaySchedul", {"isin": isin})


def get_dividend_schedule(isin: str = "", year: str = "") -> pd.DataFrame:
    """배당일정 정보"""
    p: dict = {}
    if isin:  p["isin"]  = isin
    if year:  p["divY"]  = year
    return _df("getDivSchedulInfo", p)


def get_dividend_info(isin: str, base_date: str = "") -> pd.DataFrame:
    """배당·분배금 내역 (base_date: YYYYMMDD)"""
    p = {"isin": isin}
    if base_date:
        p["basDt"] = base_date
    return _df("getDivInfo", p)


def get_odd_lot(isin: str) -> pd.DataFrame:
    """단주대금 정보"""
    return _df("getOddLotInfo", {"isin": isin})


# ── 주식정보 ──────────────────────────────────────────────────────

def get_stock_info(isin: str) -> pd.DataFrame:
    """주식 종목 정보 (발행주식수, 액면가, 시장구분 등)"""
    return _df("getStkStatInfo", {"isin": isin})


def get_unlisted_circulation(isin: str) -> pd.DataFrame:
    """비상장 유통추정 정보"""
    return _df("getUnlistCirclInfo", {"isin": isin})


def get_securities_lending(isin: str, start: str = "", end: str = "") -> pd.DataFrame:
    """종목별 대차거래 현황 (start/end: YYYYMMDD)"""
    p = {"isin": isin}
    if start: p["startBasDt"] = start
    if end:   p["endBasDt"]   = end
    return _df("getSlbDealingByIsin", p)


def get_short_code(market: str = "ALL") -> pd.DataFrame:
    """시장별 단축코드 조회 (market: KSP=코스피, KSQ=코스닥, ALL=전체)"""
    return _df("getShotnByMart", {"mrktCd": market})


def get_stock_listing(isin: str = "", market: str = "") -> pd.DataFrame:
    """주식 상장정보"""
    p: dict = {}
    if isin:   p["isin"]    = isin
    if market: p["mrktCd"]  = market
    return _df("getStkListInfo", p)


def get_stock_changes(isin: str, start: str = "", end: str = "") -> pd.DataFrame:
    """주식증감내역 (유상증자·무상증자·감자 등)"""
    p = {"isin": isin}
    if start: p["startDt"] = start
    if end:   p["endDt"]   = end
    return _df("getStkIncdecDetails", p)


def get_lockup_status(isin: str) -> pd.DataFrame:
    """의무보호예수/반환 정보"""
    return _df("getSafeDpDutyDepoStatus", {"isin": isin})


# ── 채권정보 ──────────────────────────────────────────────────────

def get_bond_issuance(isin: str = "", start: str = "", end: str = "") -> pd.DataFrame:
    """채권 발행내역"""
    p: dict = {}
    if isin:  p["isin"]      = isin
    if start: p["issuStrtDt"] = start
    if end:   p["issuEndDt"]  = end
    return _df("getBondIssuInfo", p)


def get_bond_info(isin: str) -> pd.DataFrame:
    """채권 종목 정보 (표면이율, 만기일, 발행금액 등)"""
    return _df("getBondStatInfo", {"isin": isin})


def get_interest_payment(isin: str) -> pd.DataFrame:
    """이자지급 정보"""
    return _df("getIntPayInfo", {"isin": isin})


def get_bond_early_redemption(isin: str) -> pd.DataFrame:
    """조기상환 정보"""
    return _df("getBondOptionXrcInfo", {"isin": isin})


def get_short_term_securities(isin: str = "") -> pd.DataFrame:
    """단기금융증권(CP/CD 등) 발행내역"""
    p = {"isin": isin} if isin else {}
    return _df("getShortmIssuInfo", p)


def get_cd_info(isin: str) -> pd.DataFrame:
    """CD 종목 정보"""
    return _df("getCDInfo", {"isin": isin})


def get_cp_info(isin: str) -> pd.DataFrame:
    """CP 종목 정보"""
    return _df("getCPInfo", {"isin": isin})


def get_estb_info(isin: str) -> pd.DataFrame:
    """단기사채 종목 정보"""
    return _df("getESTBInfo", {"isin": isin})


# ── 파생결합증권정보 ──────────────────────────────────────────────

def get_deriv_issuance(isin: str = "", start: str = "", end: str = "") -> pd.DataFrame:
    """파생결합증권(ELS/DLS 등) 발행내역"""
    p: dict = {}
    if isin:  p["isin"]      = isin
    if start: p["issuStrtDt"] = start
    if end:   p["issuEndDt"]  = end
    return _df("getDerivCombiIssuInfo", p)


def get_underlying_outstanding(base_asset: str = "") -> pd.DataFrame:
    """기초자산별 미상환 규모"""
    p = {"basAssetCd": base_asset} if base_asset else {}
    return _df("getBassetUnredScale", p)


def get_deriv_info(isin: str) -> pd.DataFrame:
    """파생결합증권 종목 정보"""
    return _df("getDerivCombiIsinInfo", {"isin": isin})


def get_underlying_asset(isin: str) -> pd.DataFrame:
    """기초자산 정보 조회"""
    return _df("getAssetInfo", {"isin": isin})


def get_underlying_exercise(isin: str) -> pd.DataFrame:
    """기초자산 행사정보 조회"""
    return _df("getAssetXrcInfo", {"isin": isin})


def get_redemption_condition(isin: str) -> pd.DataFrame:
    """파생결합증권 상환조건 조회"""
    return _df("getRedCondiInfo", {"isin": isin})


def get_redeemed_issues(isin: str = "", start: str = "", end: str = "") -> pd.DataFrame:
    """파생결합증권 상환종목 조회"""
    p: dict = {}
    if isin:  p["isin"]       = isin
    if start: p["redStrtDt"]  = start
    if end:   p["redEndDt"]   = end
    return _df("getRedIsinInfo", p)


# ── 외화증권정보 ──────────────────────────────────────────────────

def get_foreign_custody_by_nation(nation_cd: str = "", base_date: str = "") -> pd.DataFrame:
    """국가별 외화증권 보관현황 (nation_cd: 국가코드 2자리, base_date: YYYYMMDD)"""
    p: dict = {}
    if nation_cd:  p["natCd"]  = nation_cd
    if base_date:  p["basDt"]  = base_date
    return _df("getNationFrsecCusInfo", p)


def get_foreign_settlement_by_nation(nation_cd: str = "", base_date: str = "") -> pd.DataFrame:
    """국가별 외화증권 결제현황"""
    p: dict = {}
    if nation_cd:  p["natCd"] = nation_cd
    if base_date:  p["basDt"] = base_date
    return _df("getNationFrsecSetlInfo", p)


def get_foreign_custody_by_isin(isin: str, base_date: str = "") -> pd.DataFrame:
    """종목별 외화증권 보관현황"""
    p = {"isin": isin}
    if base_date:
        p["basDt"] = base_date
    return _df("getSecnFrsecCusInfo", p)


def get_foreign_settlement_by_isin(isin: str, base_date: str = "") -> pd.DataFrame:
    """종목별 외화증권 결제현황"""
    p = {"isin": isin}
    if base_date:
        p["basDt"] = base_date
    return _df("getSecnFrsecSetlInfo", p)
