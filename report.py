import os
import pandas as pd
from fpdf import FPDF

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/malgun.ttf",  "MalgunGothic"),
    ("C:/Windows/Fonts/gulim.ttc",   "Gulim"),
    ("/System/Library/Fonts/AppleGothic.ttf", "AppleGothic"),
]
_BLACK  = (26,  26,  26)
_GREY   = (153, 153, 153)
_LGREY  = (234, 232, 228)
_BG     = (250, 250, 248)
_WHITE  = (255, 255, 255)
_GREEN  = (27,  94,  32)


def _font(pdf: FPDF) -> str:
    for path, name in _FONT_CANDIDATES:
        if os.path.exists(path):
            pdf.add_font(name, "", path)
            return name
    raise RuntimeError("한글 폰트를 찾을 수 없습니다.")


def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(22, 22, 22)
    return pdf


def _cover_page(pdf: FPDF, f: str, title: str, subtitle: str,
                fund_name: str, fund_strategy: str, quarter: str, base_date: str) -> None:
    pdf.add_page()
    # 배경
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    # 상단 얇은 악센트 라인
    pdf.set_fill_color(*_GREEN)
    pdf.rect(0, 0, 210, 3, "F")

    # 상단 작은 라벨
    pdf.set_xy(22, 28)
    pdf.set_font(f, size=8)
    pdf.set_text_color(*_GREY)
    pdf.cell(0, 5, "SDIC  ·  PE/VC REPORT")

    # 메인 타이틀 — 크고 굵게
    pdf.set_xy(22, 60)
    pdf.set_font(f, size=36)
    pdf.set_text_color(*_BLACK)
    pdf.cell(0, 18, title)

    # 서브타이틀
    if subtitle:
        pdf.set_xy(22, 82)
        pdf.set_font(f, size=12)
        pdf.set_text_color(*_GREY)
        pdf.cell(0, 8, subtitle)

    # 구분선
    pdf.set_draw_color(*_LGREY)
    pdf.line(22, 100, 188, 100)

    # 펀드 정보 — 깔끔한 2열 레이아웃
    info = [
        ("Fund",     fund_name),
        ("Strategy", fund_strategy),
        ("Quarter",  quarter),
        ("Date",     base_date),
    ]
    pdf.set_font(f, size=9)
    for i, (k, v) in enumerate(info):
        row_y = 110 + i * 12
        pdf.set_xy(22, row_y)
        pdf.set_text_color(*_GREY)
        pdf.cell(30, 6, k)
        pdf.set_text_color(*_BLACK)
        pdf.cell(0, 6, v)

    # 하단 — 얇은 라인 + 면책 문구
    pdf.set_draw_color(*_LGREY)
    pdf.line(22, 270, 188, 270)
    pdf.set_xy(22, 274)
    pdf.set_font(f, size=7)
    pdf.set_text_color(*_GREY)
    pdf.cell(0, 5, "본 보고서는 자동 생성되었습니다. 투자 결정의 근거로 단독 사용하지 마십시오.")

    # 하단 악센트 라인
    pdf.set_fill_color(*_GREEN)
    pdf.rect(0, 294, 210, 3, "F")


def _section_header(pdf: FPDF, f: str, text: str) -> None:
    pdf.set_font(f, size=13)
    pdf.set_text_color(*_BLACK)
    pdf.cell(0, 8, text, ln=True)
    pdf.set_draw_color(*_LGREY)
    pdf.line(pdf.get_x() + 22 - 22, pdf.get_y(), 188, pdf.get_y())
    pdf.ln(4)


def _table_header(pdf: FPDF, f: str, cols: list[str], widths: list[int]) -> None:
    pdf.set_fill_color(*_BLACK)
    pdf.set_text_color(*_WHITE)
    pdf.set_font(f, size=8)
    for col, w in zip(cols, widths):
        pdf.cell(w, 7, col, border=0, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*_BLACK)


def _table_row(pdf: FPDF, f: str, vals: list, widths: list[int], shade: bool) -> None:
    pdf.set_font(f, size=8)
    if shade:
        pdf.set_fill_color(*_BG)
    else:
        pdf.set_fill_color(*_WHITE)
    for val, w in zip(vals, widths):
        pdf.cell(w, 6, str(val), border=0, align="C", fill=True)
    pdf.ln()


def _commentary_block(pdf: FPDF, f: str, text: str) -> None:
    pdf.set_font(f, size=9)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 5, text)
    pdf.set_text_color(*_BLACK)
    pdf.ln(3)


def _page_footer(pdf: FPDF, f: str) -> None:
    pdf.set_draw_color(*_LGREY)
    pdf.line(22, 285, 188, 285)
    pdf.set_xy(22, 287)
    pdf.set_font(f, size=7)
    pdf.set_text_color(*_GREY)
    pdf.cell(0, 4, f"SDIC · PE/VC Report · p.{pdf.page_no()}", align="R")
    pdf.set_text_color(*_BLACK)


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
    pdf = _new_pdf()
    f = _font(pdf)

    _cover_page(pdf, f,
                title="Quarterly Report",
                subtitle=f"포트폴리오 보고서  ·  {quarter}",
                fund_name=fund_name, fund_strategy=fund_strategy,
                quarter=quarter, base_date=base_date)

    # ─ 본문
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    _section_header(pdf, f, "Performance Summary")
    rows_ps = [
        ("MOIC",  f"{summary['펀드 MOIC']}x",  "투자원금 대비 전체 가치",        "≥ 2.0x"),
        ("IRR",   f"{round(result_df['IRR(%)'].mean(),1)}%",
                                                 "시간가치 반영 연환산 수익률",     "≥ 15%"),
        ("DPI",   f"{summary['펀드 DPI']}x",    "현금 회수 배수",                 "1.0x"),
        ("RVPI",  f"{summary['펀드 RVPI']}x",   "잔존 미실현 가치",              "—"),
        ("TVPI",  f"{summary['펀드 TVPI']}x",   "DPI + RVPI",                    "≥ 2.0x"),
    ]
    _table_header(pdf, f, ["Metric", "Value", "Description", "Benchmark"], [24, 20, 90, 32])
    for i, row in enumerate(rows_ps):
        _table_row(pdf, f, list(row), [24, 20, 90, 32], shade=(i % 2 == 0))
    pdf.ln(8)

    _section_header(pdf, f, "Portfolio Detail")
    cols_d  = ["회사명", "섹터", "단계", "투자금액(M)", "MOIC", "IRR", "DPI", "RVPI", "TVPI"]
    widths_d = [28, 20, 16, 22, 16, 16, 16, 16, 16]
    _table_header(pdf, f, cols_d, widths_d)
    for i, row in result_df.iterrows():
        vals = [
            row["회사명"], row["섹터"], row["투자단계"],
            f"{int(row['투자금액_백만원']):,}",
            f"{row['MOIC']}x", f"{row['IRR(%)']}%",
            f"{row['DPI']}x", f"{row['RVPI']}x", f"{row['TVPI']}x",
        ]
        _table_row(pdf, f, vals, widths_d, shade=(i % 2 == 0))
    pdf.ln(8)

    _section_header(pdf, f, "Commentary")
    _commentary_block(pdf, f, commentary)

    return bytes(pdf.output())


# ── 탭별 보고서 ────────────────────────────────────────────────────

def generate_jcurve_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "J-Curve Analysis", "펀드 누적 순현금흐름",
                "PE/VC 펀드", "", quarter, "")
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    _section_header(pdf, f, "Key Metrics")
    min_val     = trend_df["누적현금흐름"].min()
    current_val = trend_df["누적현금흐름"].iloc[-1]
    be          = trend_df[trend_df["누적현금흐름"] >= 0]
    be_date     = str(be["날짜"].iloc[0]) if not be.empty else "미달성"
    pdf.set_font(f, size=9)
    for label, val in [("최대 누적 손실", f"{min_val:,.0f}M"),
                       ("현재 누적 순현금흐름", f"{current_val:,.0f}M"),
                       ("Break-even", be_date)]:
        pdf.cell(0, 6, f"  {label}:  {val}", ln=True)
    pdf.ln(6)

    _section_header(pdf, f, "Cumulative Cash Flow")
    _table_header(pdf, f, ["Date", "Cumulative CF (M)"], [50, 50])
    for i, row in trend_df.iterrows():
        _table_row(pdf, f, [str(row["날짜"]), f"{row['누적현금흐름']:,.0f}"],
                   [50, 50], shade=(i % 2 == 0))
    pdf.ln(6)

    _section_header(pdf, f, "AI Analysis")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_scenario_pdf(company: str, sim_df, opt: dict, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, f"{company}", "Exit Scenario Analysis",
                company, "", quarter, "")
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    _section_header(pdf, f, "IRR by Exit Multiple")
    cols   = list(sim_df.columns)
    col_w  = 166 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in sim_df.iterrows():
        _table_row(pdf, f, [str(row[c]) for c in cols], [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "Target IRR Analysis")
    pdf.set_font(f, size=9)
    for k, v in opt.items():
        pdf.cell(0, 6, f"  {k}:  {v}", ln=True)
    pdf.ln(6)

    _section_header(pdf, f, "AI Analysis")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_quarterly_pdf(trend_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "Quarterly Trend", "분기별 펀드 지표 추이",
                "PE/VC 펀드", "", quarter, "")
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    _section_header(pdf, f, "TVPI · DPI · RVPI Trend")
    cols  = list(trend_df.columns)
    col_w = 166 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in trend_df.iterrows():
        _table_row(pdf, f, [str(row[c]) for c in cols], [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "AI Analysis")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


def generate_dart_pdf(corp_name: str, fin_df, commentary: str, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, corp_name, "DART Financial Analysis",
                corp_name, "", quarter, "")
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    _section_header(pdf, f, "Financial Statements (DART)")
    cols  = list(fin_df.columns)
    col_w = 166 // len(cols)
    _table_header(pdf, f, cols, [col_w]*len(cols))
    for i, row in fin_df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            vals.append(f"{v:,.0f}" if isinstance(v, (int, float)) else str(v))
        _table_row(pdf, f, vals, [col_w]*len(cols), shade=(i%2==0))
    pdf.ln(6)

    _section_header(pdf, f, "AI Analysis")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())


# ── 통합 보고서 (전체 탭 한 PDF) ─────────────────────────────────────

def generate_full_pdf(
    summary, result_df, df_raw, commentary,
    quarter="", fund_name="PE/VC 펀드", fund_strategy="VC", base_date="",
    jcurve_df=None, jcurve_comment="",
    trend_df=None, trend_comment="",
    rate_df=None, fx_df=None, macro_comment="", spread=None,
):
    pdf = _new_pdf()
    f = _font(pdf)

    _cover_page(pdf, f, "Full Report", f"통합 분기 보고서  ·  {quarter}",
                fund_name, fund_strategy, quarter, base_date)

    # 1. 성과 요약
    pdf.add_page()
    pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
    _section_header(pdf, f, "1. Performance Summary")
    rows_ps = [
        ("MOIC", f"{summary['펀드 MOIC']}x", "투자원금 대비 전체 가치", "≥ 2.0x"),
        ("IRR", f"{round(result_df['IRR(%)'].mean(),1)}%", "연환산 수익률", "≥ 15%"),
        ("DPI", f"{summary['펀드 DPI']}x", "현금 회수", "1.0x"),
        ("RVPI", f"{summary['펀드 RVPI']}x", "잔존 가치", "—"),
        ("TVPI", f"{summary['펀드 TVPI']}x", "DPI+RVPI", "≥ 2.0x"),
    ]
    _table_header(pdf, f, ["Metric", "Value", "Description", "BM"], [24, 20, 90, 32])
    for i, r in enumerate(rows_ps):
        _table_row(pdf, f, list(r), [24, 20, 90, 32], shade=(i % 2 == 0))
    pdf.ln(6)

    # 2. 포트폴리오 상세
    _section_header(pdf, f, "2. Portfolio Detail")
    _table_header(pdf, f, ["회사명","섹터","단계","투자(M)","MOIC","IRR","DPI","RVPI","TVPI"],
                  [28,20,16,20,16,16,16,16,18])
    for i, r in result_df.iterrows():
        _table_row(pdf, f, [r["회사명"],r["섹터"],r["투자단계"],f"{int(r['투자금액_백만원']):,}",
                   f"{r['MOIC']}x",f"{r['IRR(%)']}%",f"{r['DPI']}x",f"{r['RVPI']}x",f"{r['TVPI']}x"],
                   [28,20,16,20,16,16,16,16,18], shade=(i%2==0))
    pdf.ln(6)

    # 3. 섹터 분석
    _section_header(pdf, f, "3. Sector Analysis")
    sa = df_raw.groupby("섹터")["투자금액_백만원"].sum().sort_values(ascending=False).reset_index()
    ti = sa["투자금액_백만원"].sum()
    _table_header(pdf, f, ["섹터","투자(M)","비중(%)"], [50,50,50])
    for i, (_, r) in enumerate(sa.iterrows()):
        _table_row(pdf, f, [r["섹터"],f"{int(r['투자금액_백만원']):,}",f"{r['투자금액_백만원']/ti*100:.1f}%"],
                   [50,50,50], shade=(i%2==0))
    pdf.ln(6)

    # 4. AI 코멘터리
    _section_header(pdf, f, "4. AI Commentary")
    _commentary_block(pdf, f, commentary)

    # 5. J-Curve
    if jcurve_df is not None and not jcurve_df.empty:
        pdf.add_page()
        pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
        _section_header(pdf, f, "5. J-Curve")
        pdf.set_font(f, size=9)
        pdf.cell(0, 6, f"  최대 손실: {jcurve_df['누적현금흐름'].min():,.0f}M  |  현재: {jcurve_df['누적현금흐름'].iloc[-1]:,.0f}M", ln=True)
        pdf.ln(3)
        if jcurve_comment:
            _commentary_block(pdf, f, jcurve_comment)

    # 6. 분기별 추이
    if trend_df is not None and not trend_df.empty:
        _section_header(pdf, f, "6. Quarterly Trend")
        cols = list(trend_df.columns)
        cw = 166 // len(cols)
        _table_header(pdf, f, cols, [cw]*len(cols))
        for i, r in trend_df.iterrows():
            _table_row(pdf, f, [str(r[c]) for c in cols], [cw]*len(cols), shade=(i%2==0))
        pdf.ln(4)
        if trend_comment:
            _commentary_block(pdf, f, trend_comment)

    # 7. 거시지표
    if rate_df is not None or fx_df is not None:
        pdf.add_page()
        pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
        _section_header(pdf, f, "7. Macro Indicators")
        pdf.set_font(f, size=9)
        if rate_df is not None and not rate_df.empty:
            pdf.cell(0, 6, f"  기준금리: {rate_df['기준금리(%)'].iloc[-1]}%", ln=True)
        if fx_df is not None and not fx_df.empty:
            pdf.cell(0, 6, f"  원/달러: {fx_df['원/달러(원)'].iloc[-1]:,.0f}원", ln=True)
        if spread is not None:
            pdf.cell(0, 6, f"  IRR vs 기준금리 스프레드: {spread:+.1f}%p", ln=True)
        pdf.ln(3)
        if macro_comment:
            _commentary_block(pdf, f, macro_comment)

    return bytes(pdf.output())


def generate_macro_pdf(rate_df, fx_df, commentary: str,
                       spread: float = None, quarter: str = "") -> bytes:
    pdf = _new_pdf()
    f = _font(pdf)
    _cover_page(pdf, f, "Macro Analysis", "거시지표 분석",
                "Market Benchmark", "", quarter, "")
    pdf.add_page()
    pdf.set_fill_color(*_BG)
    pdf.rect(0, 0, 210, 297, "F")

    if not rate_df.empty:
        _section_header(pdf, f, "Base Rate (%)")
        _table_header(pdf, f, ["Period", "Rate (%)"], [50, 40])
        for i, row in rate_df.iterrows():
            _table_row(pdf, f, [row["기간"], row["기준금리(%)"]], [50, 40], shade=(i%2==0))
        pdf.ln(6)

    if not fx_df.empty:
        _section_header(pdf, f, "KRW/USD Exchange Rate")
        _table_header(pdf, f, ["Period", "Rate (KRW)"], [50, 40])
        for i, row in fx_df.iterrows():
            _table_row(pdf, f, [row["기간"], f"{row['원/달러(원)']:,.0f}"], [50, 40], shade=(i%2==0))
        pdf.ln(6)

    if spread is not None:
        pdf.set_font(f, size=9)
        pdf.cell(0, 6, f"  Fund IRR vs Base Rate Spread:  {spread:+.1f}%p", ln=True)
        pdf.ln(6)

    _section_header(pdf, f, "AI Analysis")
    _commentary_block(pdf, f, commentary)
    return bytes(pdf.output())
