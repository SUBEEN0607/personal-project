"""
포트폴리오사 현재가치 자동 추정 모듈

조회 우선순위:
  1. 상장사   → 네이버 금융에서 시가총액 × 지분율(%)
  2. 비상장사 → DART 최신 매출 × 섹터 P/S 배수 × 지분율(%)
  3. 둘 다 실패 → None (사용자 수동 입력 유지)

병렬 처리: ThreadPoolExecutor(max_workers=6)
캐싱: 모듈 레벨 dict (세션 내 중복 API 호출 방지)
"""

import re
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from dart_client import search_company, get_financials

# ── 섹터별 P/S 배수 (KOSDAQ 동종업계 중앙값, 보수적 적용) ──────────
_SECTOR_PS: dict[str, float] = {
    "SaaS": 5.0,        "SaaS/물류": 4.5,    "클라우드": 5.5,
    "바이오": 8.0,       "의료AI": 7.0,       "헬스케어": 4.0,     "제약": 5.0,
    "모빌리티": 3.0,     "자율주행": 5.0,     "물류": 2.0,
    "에듀테크": 3.5,     "교육": 2.5,
    "신재생에너지": 2.5, "ESG": 2.0,          "에너지": 2.0,
    "딥테크": 5.0,       "반도체": 6.0,       "AI": 7.0,           "로봇": 5.5,
    "애그테크": 3.0,     "푸드테크": 2.5,
    "핀테크": 4.5,       "금융": 3.0,
    "커머스": 2.0,       "리테일": 1.5,
    "콘텐츠": 3.0,       "미디어": 2.5,       "게임": 4.0,
    "부동산": 2.0,       "건설": 1.5,
    "제조": 1.8,         "화학": 1.5,
}
_DEFAULT_PS = 3.0

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── 인메모리 캐시 (세션 내 중복 조회 방지) ────────────────────────
_mktcap_cache: dict[str, float | None] = {}   # stock_code → 시총(억원)
_dart_cache:   dict[str, list] = {}            # corp_name  → search results


# ── 네이버 금융 시가총액 조회 ─────────────────────────────────────

def _naver_market_cap_억(stock_code: str) -> float | None:
    """네이버 금융 HTML → 시가총액(억원). 실패 시 None."""
    code = stock_code.zfill(6)
    if code in _mktcap_cache:
        return _mktcap_cache[code]

    try:
        from bs4 import BeautifulSoup
        url = f"https://finance.naver.com/item/main.nhn?code={code}"
        r = requests.get(url, headers=_HEADERS, timeout=8)
        if r.status_code != 200:
            _mktcap_cache[code] = None
            return None

        soup = BeautifulSoup(r.content, "html.parser")
        tag = soup.find("em", id="_market_sum")
        if not tag:
            _mktcap_cache[code] = None
            return None

        # 태그 안의 숫자들만 추출 (조/억 인코딩 깨짐 대응)
        nums = re.findall(r"[\d,]+", tag.get_text())
        nums = [n.replace(",", "") for n in nums if n.replace(",", "").isdigit()]

        if len(nums) >= 2:
            # "X조 Y억" → 숫자 2개: [X, Y] → X * 10000 + Y
            num = int(nums[0]) * 10_000 + int(nums[1])
        elif len(nums) == 1:
            # 억원 단위만 (소형주)
            num = int(nums[0])
        else:
            num = 0

        result = float(num) if num > 0 else None
        _mktcap_cache[code] = result
        return result
    except Exception:
        _mktcap_cache[code] = None
        return None


# ── 개별 조회 함수들 ─────────────────────────────────────────────

def _listed_result(corp_name: str, stock_code: str, stake_pct: float) -> dict:
    mktcap_억 = _naver_market_cap_억(stock_code)
    if mktcap_억 and stake_pct > 0:
        val_mil = round(mktcap_억 * 1_0000 * (stake_pct / 100) / 1_000_000, 0)
        return {
            "source": "상장사_시총",
            "근거": f"시총 {mktcap_억:,.0f}억 × 지분 {stake_pct}%",
            "현재가치_백만원_추정": int(val_mil),
        }
    elif mktcap_억 and stake_pct == 0:
        return {
            "source": "상장사_시총(지분율미입력)",
            "근거": f"시총 {mktcap_억:,.0f}억 — 지분율 입력 필요",
            "현재가치_백만원_추정": None,
        }
    return {
        "source": "상장사_조회실패",
        "근거": "네이버 금융 시총 조회 실패",
        "현재가치_백만원_추정": None,
    }


def _sector_multiple_result(corp_code: str, sector: str, stake_pct: float) -> dict:
    ps = _SECTOR_PS.get(sector, _DEFAULT_PS)

    fin = get_financials(corp_code, years=[2023, 2024])
    if fin.empty:
        return {
            "source": "섹터배수(재무없음)",
            "근거": f"P/S {ps}x — DART 재무제표 없음",
            "현재가치_백만원_추정": None,
        }

    latest = fin.sort_values("연도").iloc[-1]
    revenue = latest.get("매출액")
    if not revenue or revenue <= 0:
        return {
            "source": "섹터배수(매출0)",
            "근거": f"P/S {ps}x — 최근 매출 0 또는 미확인",
            "현재가치_백만원_추정": None,
        }

    # EV = 매출(원) × P/S 배수 → 전체 회사 기업가치 (백만원)
    ev_mil = revenue * ps / 1_000_000
    # 내 지분가치 (지분율 0이면 EV 전체를 참고값으로 반환)
    val_mil = round(ev_mil * (stake_pct / 100), 0) if stake_pct > 0 else round(ev_mil, 0)
    yr = int(latest["연도"])
    rev_억 = revenue / 1e8

    return {
        "source": "섹터배수",
        "근거": f"{yr}년 매출 {rev_억:.1f}억 × P/S {ps}x" + (f" × 지분 {stake_pct}%" if stake_pct > 0 else " (지분율미입력→EV전체)"),
        "현재가치_백만원_추정": int(val_mil),
    }


# ── 단일 회사 밸류에이션 결정 ─────────────────────────────────────

def resolve_one(row: dict) -> dict:
    """
    단일 포트폴리오사 처리.
    필수 keys: 회사명, 섹터, 투자금액_백만원
    선택 keys: 지분율_%  (없으면 0으로 처리)
    """
    corp_name = str(row.get("회사명", ""))
    sector    = str(row.get("섹터", ""))
    stake_pct = float(row.get("지분율_%") or 0)

    # DART 검색 (캐시 활용)
    if corp_name not in _dart_cache:
        _dart_cache[corp_name] = search_company(corp_name)
    results = _dart_cache[corp_name]

    if not results:
        return {
            **row,
            "source": "DART미등록",
            "근거": "DART 검색 결과 없음",
            "현재가치_백만원_추정": None,
        }

    best       = results[0]
    corp_code  = best["corp_code"]
    stock_code = best.get("stock_code", "") or ""

    # 상장사: 네이버 시총 우선
    if stock_code:
        res = _listed_result(corp_name, stock_code, stake_pct)
        if res["현재가치_백만원_추정"] is not None:
            return {**row, **res}
        # 조회 실패 시에도 섹터 배수로 fallback
        fallback = _sector_multiple_result(corp_code, sector, stake_pct)
        fallback["source"] = "상장사_시총실패→섹터배수"
        return {**row, **fallback}

    # 비상장사: 섹터 P/S 배수
    res = _sector_multiple_result(corp_code, sector, stake_pct)
    return {**row, **res}


# ── 병렬 벌크 처리 ───────────────────────────────────────────────

def bulk_fetch_valuations(df: pd.DataFrame, max_workers: int = 6) -> pd.DataFrame:
    """
    포트폴리오 전체를 ThreadPoolExecutor로 병렬 조회.
    반환: 원본 컬럼 + source, 근거, 현재가치_백만원_추정 추가된 DataFrame
    """
    rows    = df.to_dict("records")
    results = [None] * len(rows)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(resolve_one, row): i for i, row in enumerate(rows)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {
                    **rows[idx],
                    "source": "오류",
                    "근거": str(e),
                    "현재가치_백만원_추정": None,
                }

    return pd.DataFrame(results)
