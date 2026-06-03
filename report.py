import os
import pandas as pd
from fpdf import FPDF

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/malgun.ttf",  "MalgunGothic"),
    ("C:/Windows/Fonts/gulim.ttc",   "Gulim"),
    ("/System/Library/Fonts/AppleGothic.ttf", "AppleGothic"),
]
_GREEN  = (27,  94,  32)   # #1b5e20
_GREEN2 = (46, 125,  50)   # #2e7d32
_LGREY  = (245, 245, 245)
_MGREY  = (224, 224, 224)
_BLACK  = (26,  26,  26)
_WHITE  = (255, 255, 255)


def _font(pdf: FPDF) -> str:
    for path, name in _FONT_CANDIDATES:
        if os.path.exists(path):
            pdf.add_font(name, "", path)
            return name
    raise RuntimeError("한글 폰트를 찾을 수 없습니다. malgun.ttf 확인 필요.")


def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    return pdf


def _cover_page(pdf: FPDF, f: str, title: str, subtitle: str,
                fund_name: str, fund_strategy: str, quarter: str, base_date: str) -> None:
    """표지 페이지 (ILPA 스타일)"""
    pdf.add_page()
    # 상단 녹색 헤더 바
    pdf.set_fill_color(*_GREEN)
    pdf.rect(0, 0, 210, 42, "F")
    pdf.set_xy(18, 10)
    pdf.set_font(f, size=11)
    pdf.set_text_color(*_WHITE)
    pdf.cell(0, 7, "PE/VC 분기 보고 도우미 · SDIC", ln=True)
    pdf.set_xy(18, 18)
    pdf.set_font(f, size=9)
    pdf.cell(0, 7, f"Powered by DART · ECOS · KVIC · Claude AI", ln=True)

    pdf.set_text_color(*_BLACK)
    pdf.set_y(58)
    pdf.set_font(f, size=26)
    pdf.cell(0, 14, title, ln=True, align="C")
    if subtitle:
        pdf.set_font(f, size=13)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, subtitle, ln=True, align="C")
    pdf.set_text_color(*_BLACK)

    # 펀드 정보 박스
    pdf.set_y(96)
    pdf.set_fill_color(*_LGREY)
    pdf.set_draw_color(*_MGREY)
    pdf.rect(18, 96, 174, 52, "FD")

    info = [
        ("펀드명",  fund_name),
        ("전략",    fund_strategy),
        ("보고 분기", quarter),
        ("기준일",  base_date),
    ]
    pdf.set_font(f, size=10)
    for i, (k, v) in enumerate(info):
        row_y = 104 + i * 10
        pdf.set_xy(28, row_y)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(38, 7, k)
        pdf.set_text_color(*_BLACK)
        pdf.cell(0, 7, v, ln=True)

    # 하단 녹색 바
    pdf.set_fill_color(*_GREEN)
    pdf.rect(0, 277, 210, 20, "F")
    pdf.set_xy(18, 280)
    pdf.set_font(f, size=8)
    pdf.set_text_color(*_WHITE)
    pdf.cell(0, 6, "본 보고서는 자동 생성되었습니다. 투자 결정의 근거로 단독 사용하지 마십시오.")


def _section_header(pdf: FPDF, f: str, text: str) -> None:
    pdf.set_fill_color(*_GREEN)
    pdf.set_text_color(*_WHITE)
    pdf.set_font(f, size=11)
    pdf.cell(0, 8, f"  {text}", ln=True, fill=True)
    pdf.set_text_color(*_BLACK)
    pdf.ln(2)


def _table_header(pdf: FPDF, f: str, cols: list[str], widths: list[int]) -> None:
    pdf.set_fill_color(*_GREEN2)
    pdf.set_text_color(*_WHITE)
    pdf.set_font(f, size=9)
    for col, w in zip(cols, widths):
        pdf.cell(w, 7, col, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*_BLACK)


def _table_row(pdf: FPDF, f: str, vals: list, widths: list[int], shade: bool) -> None:
    pdf.set_font(f, size=9)
    if shade:
        pdf.set_fill_color(*_LGREY)
    else:
        pdf.set_fill_color(*_WHITE)
    for val, w in zip(vals, widths):
        pdf.cell(w, 7, str(val), border=1, align="C", fill=True)
    pdf.ln()


def _commentary_block(pdf: FPDF, f: str, text: str) -> None:
    pdf.set_font(f, size=10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, text)
    pdf.set_text_color(*_BLACK)
    pdf.ln(3)


# ── 메인 LP 보고서 ─────────────────────────────────────────────────

def generate_pdf(
    summary: dict,
    result_df: pd.DataFrame,
    commentary: str,
    quarter: str = "",
    fund_name: str = "PE/VC 펀드",
    fund_strategy: str = "벤처캐피탈(VC)",
    base_date: str = "",
) -> bytes:
    """ILPA 스타일 LP 분기 보고서"""
    pdf = _new_pdf()
    f = _font(pdf)

    # 표지
    _cover_page(pdf, f,
                title="분기 포트폴리오 보고서",
                subtitle=f"Quarterly Portfolio Report  ·  {quarter}",
                fund_name=fund_name, fund_strategy=fund_strategy,
                quarter=quarter, base_date=base_date)

    # ─ 본문 시작
    pdf.add_page()

    # 1. 성과 요약 (Performance Summary)
    _section_header(pdf, f, "1. 성과 요약 (Performance Summary)")
    rows_ps = [
        ("MOIC",          f"{summary['펀드 MOIC']}x",  "투자원금 대비 전체 가치 (실현+미실현)",      "≥ 2.0x 우수"),
        ("IRR (가중평균)", f"{round(result_df['IRR(%)'].mean(),1)}%",
                                                        "현금흐름 시간가치 반영 연환산 수익률",        "≥ 15% 우수"),
        ("DPI",           f"{summary['펀드 DPI']}x",   "LP 출자금 대비 현금 회수 배수",              "1.0x = 원금 회수"),
        ("RVPI",          f"{summary['펀드 RVPI']}x",  "LP 출자금 대비 잔존 미실현 가치 배수",       "펀드 초기 높음"),
        ("TVPI",          f"{summary['펀드 TVPI']}x",  "DPI + RVPI (총 가치 배수)",                 "≥ 2.0x 우수"),
    ]
    _table_header(pdf, f, ["지표", "값", "정의", "벤치마크"], [28, 22, 90, 34])
    for i, row in enumerate(rows_ps):
        _table_row(pdf, f, list(row), [28, 22, 90, 34], shade=(i % 2 == 0))
    pdf.ln(6)

    # 2. 포트폴리오 상세 (Portfolio Company Detail)
    _section_header(pdf, f, "2. 포트폴리오 상세 (Portfolio Company Detail)")
    cols_d  = ["회사명", "섹터", "단계", "투자금액(백만)", "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
    widths_d = [30, 22, 18, 24, 18, 18, 16, 16, 16]
    _table_header(pdf, f, cols_d, widths_d)
    for i, row in result_df.iterrows():
        vals = [
            row["회사명"], row["섹터"], row["투자단계"],
            f"{int(row['투자금액_백만원']):,}",
            f"{row['MOIC']}x", f"{row['IRR(%)']}%",
            f"{row['DPI']}x", f"{row['RVPI']}x", f"{row['TVPI']}x",
        ]
        _table_row(pdf, f, vals, widths_d, shade=(i % 2 == 0))
    pdf.ln(6)

    # 3. 분기 코멘터리 (AI)
    _section_header(pdf, f, "3. 분기 코멘터리 (AI-generated)")
    _commentary_block(pdf, f, commentary)

    return bytes(pdf.output())


# ── 탭별 보고서 ────────────────────────────────────────────────────

def generate_jcurve_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "J-Curve 분석 보고서", "펀드 누적 순현금흐름",
                "PE/VC 펀드", "", quarter, "")
    pdf.add_page()

    _section_header(pdf, f, "1. 주요 지표")
    min_val     = trend_df["누적현금흐름"].min()
    current_val = trend_df["누적현금흐름"].iloc[-1]
    be          = trend_df[trend_df["누적현금흐름"] >= 0]
    be_date     = str(be["날짜"].iloc[0]) if not be.empty else "미달성"
    pdf.set_font(f, size=10)
    for label, val in [("최대 누적 손실", f"{min_val:,.0f}백만원"),
                       ("현재 누적 순현금흐름", f"{current_val:,.0f}백만원"),
                       ("손익분기 달성 시점", be_date)]:
        pdf.cell(0, 7, f"   {label}: {val}", ln=True)
    pdf.ln(4)

    _section_header(pdf, f, "2. 누적 현금흐름 추이")
    _table_header(pdf, f, ["날짜", "누적현금흐름 (백만원)"], [60, 60])
    for i, row in trend_df.iterrows():
        _table_row(pdf, f, [str(row["날짜"]), f"{row['누적현금흐름']:,.0f}"],
                   [60, 60], shade=(i % 2 == 0))
    pdf.ln(6)

    _section_header(pdf, f, "3. AI 해석")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_scenario_pdf(company: str, sim_df, opt: dict, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, f"{company} 회수 시나리오", "Exit Scenario Analysis",
                company, "", quarter, "")
    pdf.add_page()

    _section_header(pdf, f, "1. Exit 배수별 IRR 시뮬레이션")
    cols   = list(sim_df.columns)
    col_w  = 174 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in sim_df.iterrows():
        _table_row(pdf, f, [str(row[c]) for c in cols], [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "2. 목표 IRR 달성 분석")
    pdf.set_font(f, size=10)
    for k, v in opt.items():
        pdf.cell(0, 7, f"   {k}: {v}", ln=True)
    pdf.ln(4)

    _section_header(pdf, f, "3. AI 해석")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_quarterly_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "분기별 펀드 지표 추이", "Quarterly Performance Trend",
                "PE/VC 펀드", "", quarter, "")
    pdf.add_page()

    _section_header(pdf, f, "1. TVPI / DPI / RVPI 분기 추이")
    cols  = list(trend_df.columns)
    col_w = 174 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in trend_df.iterrows():
        _table_row(pdf, f, [str(row[c]) for c in cols], [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "2. AI 해석")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_dart_pdf(corp_name: str, fin_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, f"{corp_name} 재무분석", "DART Financial Analysis",
                corp_name, "", quarter, "")
    pdf.add_page()

    _section_header(pdf, f, "1. 연도별 재무제표 (DART 공시)")
    cols  = list(fin_df.columns)
    col_w = 174 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in fin_df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            vals.append(f"{v:,.0f}" if isinstance(v, (int, float)) else str(v))
        _table_row(pdf, f, vals, [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "2. AI 재무 해석")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_macro_pdf(rate_df, fx_df, commentary: str,
                       spread: float = None, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "거시지표 분석", "Macro Economic Analysis",
                "시장 벤치마크", "", quarter, "")
    pdf.add_page()

    if not rate_df.empty:
        _section_header(pdf, f, "1. 한국은행 기준금리 추이 (%)")
        _table_header(pdf, f, ["기간", "기준금리(%)"], [60, 50])
        for i, row in rate_df.iterrows():
            _table_row(pdf, f, [row["기간"], row["기준금리(%)"]], [60, 50], shade=(i%2==0))
        pdf.ln(4)

    if not fx_df.empty:
        _section_header(pdf, f, "2. 원/달러 환율 추이 (원)")
        _table_header(pdf, f, ["기간", "원/달러(원)"], [60, 50])
        for i, row in fx_df.iterrows():
            _table_row(pdf, f, [row["기간"], f"{row['원/달러(원)']:,.0f}"], [60, 50], shade=(i%2==0))
        pdf.ln(4)

    if spread is not None:
        pdf.set_font(f, size=10)
        pdf.cell(0, 7, f"   펀드 평균 IRR vs 기준금리 스프레드: {spread:+.1f}%p", ln=True)
        pdf.ln(4)

    _section_header(pdf, f, "3. AI 거시 해석")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())
