import os
import pandas as pd
from fpdf import FPDF

# 한글 지원 폰트 후보 (우선순위 순)
_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/malgun.ttf", "MalgunGothic"),   # Windows 맑은고딕
    ("C:/Windows/Fonts/gulim.ttc",  "Gulim"),           # Windows 굴림
    ("/System/Library/Fonts/AppleGothic.ttf", "AppleGothic"),  # macOS
]


def _load_korean_font(pdf: FPDF) -> str:
    """사용 가능한 한글 폰트를 찾아 등록 후 폰트명 반환"""
    for path, name in _FONT_CANDIDATES:
        if os.path.exists(path):
            # fpdf2 2.x: uni=True 파라미터 제거됨, Unicode는 기본 지원
            pdf.add_font(name, "", path)
            return name
    return None


def generate_pdf(
    summary: dict,
    result_df: pd.DataFrame,
    commentary: str,
    quarter: str = "",
) -> bytes:
    """LP 보고서 PDF 생성 → bytes 반환"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError(
            "한글 폰트를 찾을 수 없습니다.\n"
            "C:/Windows/Fonts/malgun.ttf 파일이 있는지 확인하세요."
        )

    # ── 제목
    pdf.set_font(font, size=18)
    title = "PE/VC 포트폴리오 보고서"
    if quarter:
        title += f"  {quarter}"
    pdf.cell(0, 14, title, ln=True, align="C")
    pdf.ln(4)

    # ── 펀드 요약
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, "1. 펀드 요약", ln=True)
    pdf.set_font(font, size=10)
    skip = {"포트폴리오사 수"}
    for k, v in summary.items():
        if k not in skip:
            pdf.cell(0, 7, f"   {k}: {v}", ln=True)
    pdf.ln(4)

    # ── 포트폴리오 테이블
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, "2. 포트폴리오사별 지표", ln=True)
    pdf.set_font(font, size=9)

    cols = ["회사명", "섹터", "MOIC", "IRR(%)", "TVPI", "DPI"]
    widths = [42, 28, 22, 22, 22, 22]

    for col, w in zip(cols, widths):
        pdf.cell(w, 7, str(col), border=1, align="C")
    pdf.ln()

    for _, row in result_df.iterrows():
        for col, w in zip(cols, widths):
            pdf.cell(w, 7, str(row[col]), border=1, align="C")
        pdf.ln()
    pdf.ln(6)

    # ── 코멘터리
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, "3. 분기 코멘터리", ln=True)
    pdf.set_font(font, size=10)
    pdf.multi_cell(0, 6, commentary)

    return bytes(pdf.output())


def _header(pdf: FPDF, font: str, title: str, subtitle: str = "", quarter: str = "") -> None:
    """공통 헤더"""
    pdf.set_font(font, size=18)
    full_title = f"{title}  {quarter}" if quarter else title
    pdf.cell(0, 14, full_title, ln=True, align="C")
    if subtitle:
        pdf.set_font(font, size=11)
        pdf.cell(0, 8, subtitle, ln=True, align="C")
    pdf.ln(4)


def _section(pdf: FPDF, font: str, text: str) -> None:
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, text, ln=True)


def _commentary_block(pdf: FPDF, font: str, label: str, text: str) -> None:
    _section(pdf, font, label)
    pdf.set_font(font, size=10)
    pdf.multi_cell(0, 6, text)
    pdf.ln(3)


def generate_jcurve_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    """J-Curve 탭 보고서"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    _header(pdf, font, "J-Curve 분석 보고서", "펀드 누적 순현금흐름", quarter)

    # 주요 지표
    _section(pdf, font, "1. 주요 지표")
    pdf.set_font(font, size=10)
    min_val = trend_df["누적현금흐름"].min()
    current_val = trend_df["누적현금흐름"].iloc[-1]
    breakeven = trend_df[trend_df["누적현금흐름"] >= 0]
    be_date = str(breakeven["날짜"].iloc[0]) if not breakeven.empty else "미달성"
    for label, val in [
        ("최대 누적 손실", f"{min_val:,.0f}백만원"),
        ("현재 누적 순현금흐름", f"{current_val:,.0f}백만원"),
        ("손익분기 달성 시점", be_date),
    ]:
        pdf.cell(0, 7, f"   {label}: {val}", ln=True)
    pdf.ln(4)

    # 현금흐름 테이블
    _section(pdf, font, "2. 누적 현금흐름 추이")
    pdf.set_font(font, size=9)
    for col, w in zip(["날짜", "누적현금흐름 (백만원)"], [60, 60]):
        pdf.cell(w, 7, col, border=1, align="C")
    pdf.ln()
    for _, row in trend_df.iterrows():
        pdf.cell(60, 7, str(row["날짜"]), border=1, align="C")
        pdf.cell(60, 7, f"{row['누적현금흐름']:,.0f}", border=1, align="C")
        pdf.ln()
    pdf.ln(6)

    _commentary_block(pdf, font, "3. AI 해석", commentary)
    return bytes(pdf.output())


def generate_scenario_pdf(company: str, sim_df, opt: dict, commentary: str, quarter: str = "") -> bytes:
    """시나리오 시뮬레이터 탭 보고서"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    _header(pdf, font, f"{company} 회수 시나리오 보고서", "", quarter)

    _section(pdf, font, "1. Exit 배수별 시뮬레이션")
    pdf.set_font(font, size=9)
    cols = list(sim_df.columns)
    col_w = 190 // len(cols)
    for col in cols:
        pdf.cell(col_w, 7, str(col), border=1, align="C")
    pdf.ln()
    for _, row in sim_df.iterrows():
        for col in cols:
            pdf.cell(col_w, 7, str(row[col]), border=1, align="C")
        pdf.ln()
    pdf.ln(6)

    _section(pdf, font, "2. 목표 IRR 달성 분석")
    pdf.set_font(font, size=10)
    for k, v in opt.items():
        pdf.cell(0, 7, f"   {k}: {v}", ln=True)
    pdf.ln(4)

    _commentary_block(pdf, font, "3. AI 해석", commentary)
    return bytes(pdf.output())


def generate_quarterly_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    """분기별 추이 탭 보고서"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    _header(pdf, font, "분기별 펀드 지표 추이 보고서", "", quarter)

    _section(pdf, font, "1. TVPI / DPI / RVPI 추이")
    pdf.set_font(font, size=9)
    cols = list(trend_df.columns)
    col_w = 190 // len(cols)
    for col in cols:
        pdf.cell(col_w, 7, str(col), border=1, align="C")
    pdf.ln()
    for _, row in trend_df.iterrows():
        for col in cols:
            pdf.cell(col_w, 7, str(row[col]), border=1, align="C")
        pdf.ln()
    pdf.ln(6)

    _commentary_block(pdf, font, "2. AI 해석", commentary)
    return bytes(pdf.output())


def generate_dart_pdf(corp_name: str, fin_df, commentary: str, quarter: str = "") -> bytes:
    """DART 조회 탭 보고서"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    _header(pdf, font, f"{corp_name} DART 재무분석 보고서", "", quarter)

    _section(pdf, font, "1. 연도별 재무제표")
    pdf.set_font(font, size=9)
    cols = list(fin_df.columns)
    col_w = 190 // len(cols)
    for col in cols:
        pdf.cell(col_w, 7, str(col), border=1, align="C")
    pdf.ln()
    for _, row in fin_df.iterrows():
        for col in cols:
            val = row[col]
            if isinstance(val, (int, float)):
                val = f"{val:,.0f}"
            pdf.cell(col_w, 7, str(val), border=1, align="C")
        pdf.ln()
    pdf.ln(6)

    _commentary_block(pdf, font, "2. AI 재무 해석", commentary)
    return bytes(pdf.output())


def generate_macro_pdf(rate_df, fx_df, commentary: str, spread: float = None, quarter: str = "") -> bytes:
    """거시지표 탭 보고서"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_korean_font(pdf)
    if font is None:
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    _header(pdf, font, "거시지표 분석 보고서", "기준금리 · 환율 · 포트폴리오 맥락", quarter)

    if not rate_df.empty:
        _section(pdf, font, "1. 한국은행 기준금리 추이 (%)")
        pdf.set_font(font, size=9)
        for col, w in zip(["기간", "기준금리(%)"], [60, 50]):
            pdf.cell(w, 7, col, border=1, align="C")
        pdf.ln()
        for _, row in rate_df.iterrows():
            pdf.cell(60, 7, str(row["기간"]), border=1, align="C")
            pdf.cell(50, 7, str(row["기준금리(%)"]), border=1, align="C")
            pdf.ln()
        pdf.ln(4)

    if not fx_df.empty:
        _section(pdf, font, "2. 원/달러 환율 추이 (원)")
        pdf.set_font(font, size=9)
        for col, w in zip(["기간", "원/달러(원)"], [60, 50]):
            pdf.cell(w, 7, col, border=1, align="C")
        pdf.ln()
        for _, row in fx_df.iterrows():
            pdf.cell(60, 7, str(row["기간"]), border=1, align="C")
            pdf.cell(50, 7, f"{row['원/달러(원)']:,.0f}", border=1, align="C")
            pdf.ln()
        pdf.ln(4)

    if spread is not None:
        pdf.set_font(font, size=10)
        pdf.cell(0, 7, f"   펀드 평균 IRR vs 기준금리 스프레드: {spread:+.1f}%p", ln=True)
        pdf.ln(4)

    _commentary_block(pdf, font, "3. AI 거시 해석", commentary)
    return bytes(pdf.output())
