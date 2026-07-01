import os
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        # 1순위: 환경변수, 2순위: Streamlit Cloud secrets
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = (st.secrets.get("ANTHROPIC_API_KEY")
                           or st.secrets.get("anthropic_api_key"))
            except Exception:
                pass
        if api_key:
            _client = Anthropic(api_key=api_key)
        else:
            _client = Anthropic()  # SDK 자체 환경변수 탐색 시도
    return _client


def generate_commentary(summary: dict, detail_rows: list[dict]) -> str:
    """펀드 요약 및 포트폴리오 데이터를 바탕으로 분기 코멘터리 생성"""

    portfolio_text = "\n".join(
        f"- {r['회사명']}: MOIC {r['MOIC']}x, IRR {r['IRR(%)']}%, TVPI {r['TVPI']}x"
        for r in detail_rows
    )

    # Top/Bottom 분석
    sorted_rows = sorted(detail_rows, key=lambda x: x["MOIC"], reverse=True)
    top_name = sorted_rows[0]["회사명"] if sorted_rows else ""
    top_moic = sorted_rows[0]["MOIC"] if sorted_rows else 0
    bottom_name = sorted_rows[-1]["회사명"] if sorted_rows else ""
    bottom_moic = sorted_rows[-1]["MOIC"] if sorted_rows else 0

    # 집중도 계산
    if "투자금액_백만원" in detail_rows[0]:
        total_inv = sum(r.get("투자금액_백만원", 0) for r in detail_rows)
        weights = [r.get("투자금액_백만원", 0) / total_inv for r in detail_rows] if total_inv > 0 else []
        hhi = round(sum(w ** 2 for w in weights) * 10000)
    else:
        hhi = 0

    prompt = f"""당신은 PE/VC 운용사의 분기 보고서를 작성하는 시니어 애널리스트입니다.
아래 펀드 성과 데이터를 바탕으로 LP 보고서용 한국어 코멘터리를 작성해주세요.

[펀드 요약]
- 포트폴리오사 수: {summary['포트폴리오사 수']}개
- 총 투자금액: {summary['총 투자금액 (백만원)']:,}백만원
- 펀드 MOIC: {summary['펀드 MOIC']}x
- 펀드 TVPI: {summary['펀드 TVPI']}x
- 펀드 DPI: {summary['펀드 DPI']}x (현금 회수 배수)
- 펀드 RVPI: {summary['펀드 RVPI']}x (잔존 가치 배수)

[포트폴리오사별 주요 지표]
{portfolio_text}

[추가 분석 데이터]
- 최고 성과: {top_name} (MOIC {top_moic}x)
- 최저 성과: {bottom_name} (MOIC {bottom_moic}x)
- 포트폴리오 집중도 HHI: {hhi} (2500 이상이면 집중 리스크)

작성 구조 (5개 섹션, 각 2~3문장):
1. 전체 성과 총평 — MOIC/IRR/TVPI 기준 펀드 전반 평가. 벤치마크(MOIC 2.0x, IRR 15%) 대비 성과 언급.
2. Top Performer 분석 — 최고 성과 포트폴리오사의 성장 요인 및 향후 전망.
3. 리스크 요인 — MOIC 1.0x 미만 기업이 있으면 원인 분석. 집중도 리스크가 높으면 분산 필요성 언급.
4. DPI vs RVPI 분석 — 현금 회수 진행 상황 평가. DPI가 낮으면 회수 지연 원인, 높으면 조기 회수 성과 언급.
5. 향후 전략 제언 — 후속 투자, Exit 타이밍, 포트폴리오 리밸런싱 방향성 제시.

작성 조건:
- 숫자는 반드시 포함하고 LP가 바로 활용할 수 있는 수준으로 작성
- 전문적이고 간결한 한국어 사용
- 절대로 굵은글씨, 기울임, 제목 등 마크다운 문법을 사용하지 마세요. 순수 텍스트만 작성하세요."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def interpret_jcurve(trend_df) -> str:
    """J-Curve 누적 현금흐름 데이터 해석"""
    min_val = trend_df["누적현금흐름"].min()
    max_val = trend_df["누적현금흐름"].max()
    current_val = trend_df["누적현금흐름"].iloc[-1]
    breakeven_rows = trend_df[trend_df["누적현금흐름"] >= 0]
    breakeven_date = breakeven_rows["날짜"].iloc[0] if not breakeven_rows.empty else "미달성"

    prompt = f"""PE/VC 펀드의 J-Curve 분석 전문가로서 아래 데이터를 해석해주세요.

[J-Curve 주요 지표]
- 최대 누적 손실(투자 집행 최고점): {min_val:,.0f}백만원
- 현재 누적 순현금흐름: {current_val:,.0f}백만원
- 손익분기 달성: {breakeven_date}
- 최대 누적 수익: {max_val:,.0f}백만원

조건:
1. J-Curve 형태 분석 (현재 어느 단계인지)
2. 손익분기 시점 평가
3. 투자 회수 진행 속도에 대한 LP 관점 코멘트
4. 2~3문단, 전문적인 한국어로 작성
5. 절대로 **굵은글씨**, *기울임*, #제목 등 마크다운 문법을 사용하지 마세요. 순수 텍스트만 작성하세요."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def interpret_scenario(company: str, sim_df, opt: dict) -> str:
    """회수 시나리오 시뮬레이션 결과 해석"""
    sim_text = "\n".join(
        f"- Exit {row['Exit 배수']}x → IRR {row['IRR (%)']}%, 회수금액 {row['회수금액 (백만원)']:,}백만원"
        for _, row in sim_df.iterrows()
    )
    min_multiple = list(opt.values())[0] if opt else "N/A"

    prompt = f"""PE/VC 투자 회수 전략 전문가로서 {company}의 시나리오 분석을 해석해주세요.

[회수 시나리오]
{sim_text}

[목표 IRR 달성 최소 배수]
{min_multiple}

조건:
1. 최적 회수 타이밍 및 목표 배수 제시
2. 리스크 시나리오(낮은 배수) vs 기대 시나리오 비교
3. IRR 20% 달성 가능성 평가
4. 2~3문단, LP/GP에게 전달 가능한 수준의 한국어 작성"""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def interpret_quarterly_trend(trend_df) -> str:
    """분기별 TVPI/DPI/RVPI 추이 해석"""
    latest = trend_df.iloc[-1]
    first = trend_df.iloc[0]
    quarters = len(trend_df)

    prompt = f"""PE/VC 펀드 성과 분석 전문가로서 분기별 추이 데이터를 해석해주세요.

[추이 요약]
- 분석 분기 수: {quarters}개 분기
- 초기 TVPI: {first['TVPI']}x → 최근 TVPI: {latest['TVPI']}x
- 초기 DPI: {first['DPI']}x → 최근 DPI: {latest['DPI']}x
- 초기 RVPI: {first['RVPI']}x → 최근 RVPI: {latest['RVPI']}x

[전체 추이 데이터]
{trend_df.to_string(index=False)}

조건:
1. TVPI 개선 또는 하락 추세 분석
2. DPI(실현) vs RVPI(미실현) 비중 변화 해석
3. 분기별 주요 변곡점 식별
4. 2~3문단, 전문적인 한국어로 작성
5. 절대로 **굵은글씨**, *기울임*, #제목 등 마크다운 문법을 사용하지 마세요. 순수 텍스트만 작성하세요."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def interpret_dart_financials(corp_name: str, fin_df) -> str:
    """DART 재무제표 데이터 해석"""
    fin_text = fin_df.to_string(index=False)

    prompt = f"""PE/VC 투자 심사역으로서 {corp_name}의 DART 재무제표를 해석해주세요.

[재무제표 데이터 (단위: 원)]
{fin_text}

조건:
1. 매출 성장률 및 수익성(영업이익률, 순이익률) 계산 및 평가
2. 재무 건전성 및 성장 모멘텀 분석
3. PE/VC 투자자 관점에서의 투자 가치 평가
4. 2~3문단, 투자 심사 보고서 수준의 한국어로 작성
5. 절대로 **굵은글씨**, *기울임*, #제목 등 마크다운 문법을 사용하지 마세요. 순수 텍스트만 작성하세요."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def interpret_macro(rate_df, fx_df, spread: float = None) -> str:
    """거시지표(기준금리, 환율) 해석"""
    latest_rate = rate_df["기준금리(%)"].iloc[-1] if not rate_df.empty else "N/A"
    rate_chg = (
        round(rate_df["기준금리(%)"].iloc[-1] - rate_df["기준금리(%)"].iloc[0], 2)
        if len(rate_df) > 1 else 0
    )
    latest_fx = fx_df["원/달러(원)"].iloc[-1] if not fx_df.empty else "N/A"
    fx_chg = (
        round(fx_df["원/달러(원)"].iloc[-1] - fx_df["원/달러(원)"].iloc[0], 0)
        if len(fx_df) > 1 else 0
    )

    spread_text = f"펀드 평균 IRR vs 기준금리 스프레드: {spread:+.1f}%p" if spread is not None else ""

    prompt = f"""PE/VC 거시경제 분석 전문가로서 아래 지표를 해석하고 포트폴리오에 미치는 영향을 분석해주세요.

[한국은행 기준금리]
- 현재 기준금리: {latest_rate}%
- 조회 기간 변동: {rate_chg:+.2f}%p

[원/달러 환율]
- 현재 환율: {latest_fx:,.0f}원
- 조회 기간 변동: {fx_chg:+.0f}원

{spread_text}

조건:
1. 금리 변동이 PE/VC 투자 환경에 미치는 영향
2. 환율 변동이 해외 투자 포트폴리오 및 IRR에 미치는 영향
3. 현 거시 환경에서의 투자 전략 시사점
4. 2~3문단, 전문적인 한국어로 작성
5. 절대로 **굵은글씨**, *기울임*, #제목 등 마크다운 문법을 사용하지 마세요. 순수 텍스트만 작성하세요."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


if __name__ == "__main__":
    from calculator import load_portfolio, run_all, portfolio_summary

    df = load_portfolio("sample_portfolio.csv")
    result_df = run_all(df)
    summary = portfolio_summary(df)

    detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
    commentary = generate_commentary(summary, detail_rows)

    print("=== Claude 코멘터리 ===")
    print(commentary)
