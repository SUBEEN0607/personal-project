"""
포트폴리오사 현재가치 자동 추정 모듈 v2

조회 우선순위:
  1. 상장사   → 네이버 금융 시가총액 × 지분율
  2. 비상장사 → DART 재무 기반 멀티플 (P/S·EV/EBITDA·P/E·DCF-lite) 가중 평균
  3. 둘 다 실패 → None

출력 키 (기존 호환 유지):
  현재가치_백만원_추정  → Base 시나리오 값 (앱·장표 그대로 사용)
  source, 근거, method_detail → 기존과 동일
  시나리오              → {보수: int, 기준: int, 낙관: int}  ← 추가
  신뢰도               → "High" / "Medium" / "Low"         ← 추가
"""

import re
import math
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from dart_client import search_company, get_financials

# ── 섹터별 P/S 범위 (보수 / 기준 / 낙관) ──────────────────────────
# 출처: KOSDAQ 동종업 중앙값 기반 + VC 관행 할인율 적용
_SECTOR_PS_RANGE: dict[str, tuple[float, float, float]] = {
    # (bear, base, bull)
    "SaaS":          (3.0,  5.0,  9.0),
    "SaaS/물류":     (2.5,  4.5,  7.5),
    "클라우드":      (3.5,  5.5,  9.5),
    "바이오":        (4.0,  8.0, 15.0),
    "의료AI":        (4.0,  7.0, 12.0),
    "헬스케어":      (2.5,  4.0,  7.0),
    "제약":          (3.0,  5.0,  9.0),
    "모빌리티":      (1.5,  3.0,  5.5),
    "자율주행":      (3.0,  5.0,  9.0),
    "물류":          (1.0,  2.0,  3.5),
    "에듀테크":      (2.0,  3.5,  6.0),
    "교육":          (1.5,  2.5,  4.0),
    "신재생에너지":  (1.5,  2.5,  4.5),
    "ESG":           (1.2,  2.0,  3.5),
    "에너지":        (1.0,  2.0,  3.5),
    "딥테크":        (3.0,  5.0,  9.0),
    "반도체":        (3.5,  6.0, 10.0),
    "AI":            (4.0,  7.0, 13.0),
    "로봇":          (3.0,  5.5,  9.5),
    "애그테크":      (1.5,  3.0,  5.5),
    "푸드테크":      (1.5,  2.5,  4.5),
    "핀테크":        (2.5,  4.5,  8.0),
    "금융":          (1.5,  3.0,  5.0),
    "커머스":        (1.0,  2.0,  3.5),
    "리테일":        (0.8,  1.5,  2.5),
    "콘텐츠":        (1.5,  3.0,  5.5),
    "미디어":        (1.2,  2.5,  4.5),
    "게임":          (2.0,  4.0,  7.0),
    "부동산":        (1.0,  2.0,  3.5),
    "건설":          (0.8,  1.5,  2.5),
    "제조":          (0.8,  1.8,  3.0),
    "화학":          (0.7,  1.5,  2.5),
}
_DEFAULT_PS_RANGE = (1.5, 3.0, 5.5)

# Rule of 40 프리미엄 적용 섹터 (SaaS·소프트웨어 중심)
_RULE40_SECTORS = {"SaaS", "SaaS/물류", "클라우드", "AI", "딥테크", "의료AI", "핀테크", "에듀테크"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_mktcap_cache: dict[str, float | None] = {}
_dart_cache:   dict[str, list]         = {}


# ── 상장사: 네이버 금융 시가총액 ──────────────────────────────────

def _naver_market_cap_억(stock_code: str) -> float | None:
    code = stock_code.zfill(6)
    if code in _mktcap_cache:
        return _mktcap_cache[code]
    try:
        from bs4 import BeautifulSoup
        url = f"https://finance.naver.com/item/main.nhn?code={code}"
        r = requests.get(url, headers=_HEADERS, timeout=6)
        if r.status_code != 200:
            _mktcap_cache[code] = None
            return None
        soup = BeautifulSoup(r.content, "html.parser")
        tag = soup.find("em", id="_market_sum")
        if not tag:
            _mktcap_cache[code] = None
            return None
        nums = [n.replace(",", "") for n in re.findall(r"[\d,]+", tag.get_text())
                if n.replace(",", "").isdigit()]
        if len(nums) >= 2:
            num = int(nums[0]) * 10_000 + int(nums[1])
        elif len(nums) == 1:
            num = int(nums[0])
        else:
            num = 0
        result = float(num) if num > 0 else None
        _mktcap_cache[code] = result
        return result
    except Exception:
        _mktcap_cache[code] = None
        return None


def _listed_result(corp_name: str, stock_code: str, stake_pct: float) -> dict:
    mktcap_억 = _naver_market_cap_억(stock_code)
    if mktcap_억 and stake_pct > 0:
        # mktcap_억 단위: 억원 → 1억원 = 100백만원
        val_mil = round(mktcap_억 * 100 * (stake_pct / 100), 0)
        mktcap_str = f"{mktcap_억/10000:.1f}조" if mktcap_억 >= 10000 else f"{mktcap_억:,.0f}억"
        return {
            "source": "상장사_시총",
            "근거": f"시총 {mktcap_str} × 지분 {stake_pct}% = {val_mil:,.0f}백만원",
            "현재가치_백만원_추정": int(val_mil),
            "시나리오": {
                "보수": int(val_mil * 0.80),
                "기준": int(val_mil),
                "낙관": int(val_mil * 1.20),
            },
            "신뢰도": "High",
            "method_detail": {"시가총액_억": mktcap_억, "지분율": stake_pct},
        }
    if mktcap_억 and stake_pct == 0:
        mktcap_str = f"{mktcap_억/10000:.1f}조" if mktcap_억 >= 10000 else f"{mktcap_억:,.0f}억"
        return {
            "source": "상장사_시총(지분율미입력)",
            "근거": f"시총 {mktcap_str} — 지분율 입력 필요",
            "현재가치_백만원_추정": None,
            "시나리오": None,
            "신뢰도": "Low",
            "method_detail": {"시가총액_억": mktcap_억},
        }
    return {
        "source": "상장사_조회실패",
        "근거": "네이버 금융 시총 조회 실패",
        "현재가치_백만원_추정": None,
        "시나리오": None,
        "신뢰도": "Low",
        "method_detail": None,
    }


# ── 재무 분석 헬퍼 ────────────────────────────────────────────────

def _calc_cagr(fin_sorted: pd.DataFrame) -> float | None:
    """3년 이상이면 CAGR, 2년이면 YoY, 1년이면 None."""
    rev_rows = fin_sorted[fin_sorted["매출액"].notna() & (fin_sorted["매출액"] > 0)]
    if len(rev_rows) < 2:
        return None
    first = rev_rows.iloc[0]
    last  = rev_rows.iloc[-1]
    n = int(last["연도"]) - int(first["연도"])
    if n <= 0:
        return None
    cagr = (last["매출액"] / first["매출액"]) ** (1 / n) - 1
    return round(cagr * 100, 1)


def _stage_factor(stage: str) -> tuple[float, str]:
    """투자단계 → (배수 조정 계수, 설명)"""
    s = stage.lower()
    if any(k in s for k in ["seed", "pre-a", "pre_a", "시드", "프리"]):
        return 0.75, "Seed/Pre-A -25%"
    if any(k in s for k in ["series a", "시리즈 a", "시리즈a"]):
        return 0.88, "Series A -12%"
    if any(k in s for k in ["series b", "시리즈 b", "시리즈b"]):
        return 1.00, ""
    if any(k in s for k in ["series c", "시리즈 c", "시리즈c", "series d", "시리즈 d"]):
        return 1.12, "Series C+ +12%"
    if any(k in s for k in ["pre-ipo", "pre ipo", "ipo"]):
        return 1.20, "Pre-IPO +20%"
    return 1.00, ""


def _growth_factor(cagr: float | None) -> tuple[float, str]:
    """CAGR → (배수 조정 계수, 설명)"""
    if cagr is None:
        return 1.00, ""
    if cagr >= 60:
        return 1.40, f"CAGR {cagr:+.0f}% → +40%"
    if cagr >= 40:
        return 1.25, f"CAGR {cagr:+.0f}% → +25%"
    if cagr >= 20:
        return 1.10, f"CAGR {cagr:+.0f}% → +10%"
    if cagr >= 0:
        return 1.00, ""
    if cagr >= -15:
        return 0.88, f"CAGR {cagr:+.0f}% → -12%"
    return 0.75, f"CAGR {cagr:+.0f}% → -25%"


def _confidence(fin_sorted: pd.DataFrame, n_methods: int, latest_yr: int) -> str:
    """데이터 풍부도·최신성·방법 수 기반 신뢰도"""
    score = 0
    score += min(len(fin_sorted), 3)          # 최대 3점 (재무연도 수)
    score += min(n_methods, 3)                # 최대 3점 (밸류에이션 방법 수)
    score += 2 if latest_yr >= 2024 else (1 if latest_yr >= 2023 else 0)
    if score >= 7:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def _dcf_lite(revenue: float, cagr: float | None, op_margin: float | None,
              terminal_ps: float) -> float | None:
    """
    간이 DCF: 3년 포워드 매출 추정 후 터미널 배수 적용.
    EV = Σ FCF_t/(1+WACC)^t  + TV/(1+WACC)^3
    FCF ≈ Revenue × op_margin × 0.7  (세후 영업이익 근사)
    TV  = Year3_Revenue × terminal_ps
    WACC = 15% (VC 포트폴리오 표준)
    """
    if revenue <= 0:
        return None
    g = max(min((cagr or 10) / 100, 0.60), -0.10)  # 성장률 클램프
    wacc = 0.15
    fcf_margin = max((op_margin or 5) / 100 * 0.7, 0.02)  # 최소 2%

    ev = 0.0
    rev = revenue
    for t in range(1, 4):
        rev *= (1 + g)
        fcf = rev * fcf_margin
        ev += fcf / (1 + wacc) ** t
    # 터미널 밸류 (3년 후 매출 × terminal_ps)
    tv = rev * terminal_ps
    ev += tv / (1 + wacc) ** 3
    return ev / 1_000_000  # 원 → 백만원


# ── 비상장사 멀티플 밸류에이션 ───────────────────────────────────

def _sector_multiple_result(corp_code: str, sector: str, stake_pct: float,
                             stage: str = "", cost_basis_mil: float = 0) -> dict:
    ps_bear, ps_base, ps_bull = _SECTOR_PS_RANGE.get(sector, _DEFAULT_PS_RANGE)

    fin = get_financials(corp_code, years=[2022, 2023, 2024])
    if fin.empty:
        return {
            "source": "섹터배수(재무없음)",
            "근거": f"섹터 P/S {ps_base}x — DART 재무제표 없음",
            "현재가치_백만원_추정": None,
            "시나리오": None,
            "신뢰도": "Low",
            "method_detail": None,
        }

    fin_sorted = fin.sort_values("연도").reset_index(drop=True)
    latest     = fin_sorted.iloc[-1]
    revenue    = latest.get("매출액")
    op_income  = latest.get("영업이익")
    net_income = latest.get("당기순이익")
    yr         = int(latest["연도"])

    # ── 성장률 (3년 CAGR 우선) ──
    cagr = _calc_cagr(fin_sorted)

    # ── 영업이익률 ──
    op_margin = None
    if revenue and revenue > 0 and op_income:
        op_margin = round(op_income / revenue * 100, 1)

    # ── 스테이지 / 성장 조정 계수 ──
    stage_f, stage_note = _stage_factor(stage)
    growth_f, growth_note = _growth_factor(cagr)
    adj_f = stage_f * growth_f
    adj_notes = [n for n in [stage_note, growth_note] if n]

    # ── Rule of 40 프리미엄 (SaaS/Tech 계열 흑자 성장기업) ──
    rule40_note = ""
    if sector in _RULE40_SECTORS and cagr is not None and op_margin is not None:
        r40 = cagr + op_margin
        if r40 >= 60:
            adj_f *= 1.25; rule40_note = f"Rule40={r40:.0f} → +25%"
        elif r40 >= 40:
            adj_f *= 1.12; rule40_note = f"Rule40={r40:.0f} → +12%"
    if rule40_note:
        adj_notes.append(rule40_note)
    adj_note_str = " · ".join(adj_notes) if adj_notes else "기본 배수"

    # ── 매출 기준값 (3년 평균 vs 최신, 보수적) ──
    rev_vals = fin_sorted["매출액"].dropna()
    rev_vals = rev_vals[rev_vals > 0]
    rev_base = float(rev_vals.mean()) if len(rev_vals) >= 2 else (float(revenue) if revenue else 0)

    # ── 매출 없을 때: EV/EBIT 단독 ──
    if rev_base <= 0:
        if op_income and op_income > 0:
            ebit_mult = ps_base * 8
            ev = op_income * ebit_mult / 1_000_000 * adj_f
            val_mil = round(ev * (stake_pct / 100), 0) if stake_pct > 0 else round(ev, 0)
            return {
                "source": "EV/EBIT(매출없음)",
                "근거": f"{yr}년 영업이익 {op_income/1e8:.1f}억 × EV/EBIT {ebit_mult:.0f}x",
                "현재가치_백만원_추정": int(val_mil),
                "시나리오": {"보수": int(val_mil*0.75), "기준": int(val_mil), "낙관": int(val_mil*1.35)},
                "신뢰도": "Low",
                "method_detail": {"연도": yr, "적용방법": "EV/EBIT"},
            }
        return {
            "source": "섹터배수(데이터부족)",
            "근거": f"섹터 P/S {ps_base}x — {yr}년 재무 데이터 부족",
            "현재가치_백만원_추정": None,
            "시나리오": None,
            "신뢰도": "Low",
            "method_detail": None,
        }

    rev_억 = rev_base / 1e8
    methods: dict[str, dict] = {}

    # ── 방법 1: P/S (조정 배수 × Bear/Base/Bull) ──
    def _ps_ev(ps): return rev_base * ps * adj_f / 1_000_000
    methods["P/S"] = {
        "ev_bear": _ps_ev(ps_bear),
        "ev_base": _ps_ev(ps_base),
        "ev_bull": _ps_ev(ps_bull),
        "label": f"{rev_억:.1f}억매출 × P/S {round(ps_base*adj_f,1)}x",
        "weight": 3,
    }

    # ── 방법 2: EV/EBITDA ──
    if op_income and op_income > 0:
        ebitda_base = max(ps_base * 6, 8.0)
        ebitda_bear = max(ps_bear * 6, 5.0)
        ebitda_bull = ps_bull * 7
        def _ebitda_ev(m): return op_income * m * adj_f / 1_000_000
        methods["EV/EBITDA"] = {
            "ev_bear": _ebitda_ev(ebitda_bear),
            "ev_base": _ebitda_ev(ebitda_base),
            "ev_bull": _ebitda_ev(ebitda_bull),
            "label": f"영업이익 {op_income/1e8:.1f}억 × {ebitda_base:.0f}x",
            "weight": 2,
        }

    # ── 방법 3: P/E ──
    if net_income and net_income > 0:
        pe_base = max(ps_base * 12, 15.0)
        pe_bear = max(ps_bear * 10, 10.0)
        pe_bull = ps_bull * 14
        def _pe_ev(m): return net_income * m * adj_f / 1_000_000
        methods["P/E"] = {
            "ev_bear": _pe_ev(pe_bear),
            "ev_base": _pe_ev(pe_base),
            "ev_bull": _pe_ev(pe_bull),
            "label": f"순이익 {net_income/1e8:.1f}억 × P/E {pe_base:.0f}x",
            "weight": 1,
        }

    # ── 방법 4: DCF-lite ──
    dcf_ev = _dcf_lite(rev_base, cagr, op_margin, ps_base)
    if dcf_ev and dcf_ev > 0:
        methods["DCF-lite"] = {
            "ev_bear": dcf_ev * 0.75,
            "ev_base": dcf_ev,
            "ev_bull": dcf_ev * 1.40,
            "label": f"3yr포워드 WACC15% TV={ps_base}x",
            "weight": 2,
        }

    # ── 가중 평균 EV ──
    total_w = sum(v["weight"] for v in methods.values())
    ev_bear = sum(v["ev_bear"] * v["weight"] for v in methods.values()) / total_w
    ev_base = sum(v["ev_base"] * v["weight"] for v in methods.values()) / total_w
    ev_bull = sum(v["ev_bull"] * v["weight"] for v in methods.values()) / total_w

    # ── 하방 보호 Floor ──
    # Bear 시나리오: 투자원가의 30% 이하로는 안 내림
    floor = cost_basis_mil * 0.30 if cost_basis_mil > 0 else 0
    ev_bear = max(ev_bear, floor / (stake_pct / 100) if stake_pct > 0 else floor)

    # ── 지분율 반영 ──
    def _apply_stake(ev_mil):
        if stake_pct > 0:
            return round(ev_mil * (stake_pct / 100), 0)
        return round(ev_mil, 0)

    val_bear = int(_apply_stake(ev_bear))
    val_base = int(_apply_stake(ev_base))
    val_bull = int(_apply_stake(ev_bull))

    # ── 신뢰도 ──
    conf = _confidence(fin_sorted, len(methods), yr)

    # ── 근거 문자열 ──
    parts = [f"{yr}년 기준", f"매출평균 {rev_억:.1f}억"]
    if op_margin is not None:
        parts.append(f"영업이익률 {op_margin:.1f}%")
    if cagr is not None:
        parts.append(f"CAGR {cagr:+.1f}%")
    parts.append(f"[{adj_note_str}]")
    methods_summary = " / ".join(
        f"{k}={v['ev_base']/100:.0f}억(w{v['weight']})" for k, v in methods.items()
    )
    parts.append(f"[{methods_summary}]")
    parts.append(f"EV가중기준 {ev_base/100:.0f}억")
    if stake_pct > 0:
        parts.append(f"× 지분 {stake_pct}%")

    source = f"멀티플가중({len(methods)}개 메서드·{conf})" if len(methods) > 1 else "P/S섹터배수"

    return {
        "source": source,
        "근거": " | ".join(parts),
        "현재가치_백만원_추정": val_base,
        "시나리오": {"보수": val_bear, "기준": val_base, "낙관": val_bull},
        "신뢰도": conf,
        "method_detail": {
            "연도": yr,
            "매출평균_억": round(rev_억, 1),
            "영업이익률_%": op_margin,
            "CAGR_%": cagr,
            "조정계수": round(adj_f, 3),
            "조정사유": adj_note_str,
            "섹터PS범위": {"보수": ps_bear, "기준": ps_base, "낙관": ps_bull},
            "메서드수": len(methods),
            "메서드별EV_억": {
                k: {"보수": round(v["ev_bear"]/100, 0),
                    "기준": round(v["ev_base"]/100, 0),
                    "낙관": round(v["ev_bull"]/100, 0)}
                for k, v in methods.items()
            },
            "EV가중평균_억": {
                "보수": round(ev_bear/100, 0),
                "기준": round(ev_base/100, 0),
                "낙관": round(ev_bull/100, 0),
            },
        },
    }


# ── 단일 회사 밸류에이션 ──────────────────────────────────────────

def resolve_one(row: dict) -> dict:
    corp_name      = str(row.get("회사명", ""))
    sector         = str(row.get("섹터", ""))
    stage          = str(row.get("투자단계", ""))
    stake_pct      = float(row.get("지분율_%") or 0)
    cost_basis_mil = float(row.get("투자금액_백만원") or 0)

    if corp_name not in _dart_cache:
        _dart_cache[corp_name] = search_company(corp_name)
    results = _dart_cache[corp_name]

    if not results:
        return {
            **row,
            "source": "DART미등록",
            "근거": "DART 검색 결과 없음 — 회사명 확인 필요",
            "현재가치_백만원_추정": None,
            "시나리오": None,
            "신뢰도": "Low",
        }

    best       = results[0]
    corp_code  = best["corp_code"]
    stock_code = best.get("stock_code", "") or ""

    if stock_code:
        res = _listed_result(corp_name, stock_code, stake_pct)
        if res["현재가치_백만원_추정"] is not None:
            return {**row, **res}
        fallback = _sector_multiple_result(corp_code, sector, stake_pct, stage, cost_basis_mil)
        fallback["source"] = "상장사_시총실패→섹터배수"
        return {**row, **fallback}

    res = _sector_multiple_result(corp_code, sector, stake_pct, stage, cost_basis_mil)
    return {**row, **res}


# ── 병렬 벌크 처리 ───────────────────────────────────────────────

def bulk_fetch_valuations(df: pd.DataFrame, max_workers: int = 6) -> pd.DataFrame:
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
                    "시나리오": None,
                    "신뢰도": "Low",
                }

    return pd.DataFrame(results)
