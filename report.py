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
    pdf.cell(0, 5, "본 보고서는 자동 생성된 참고 자료입니다. 투자 결정의 근거로 단독 사용할 수 없습니다.")

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
    import numpy as np

    _cover_page(pdf, f, "Quarterly Report", f"분기 보고서 (참고용)  ·  {quarter}",
                fund_name, fund_strategy, quarter, base_date)

    avg_irr = round(result_df["IRR(%)"].mean(), 1)

    # ── 1. 성과 요약 ──
    pdf.add_page()
    pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
    _section_header(pdf, f, "1. Performance Summary")
    rows_ps = [
        ("MOIC", f"{summary['펀드 MOIC']}x", "투자원금 대비 전체 가치", "2.0x"),
        ("IRR", f"{avg_irr}%", "연환산 수익률", "15%"),
        ("DPI", f"{summary['펀드 DPI']}x", "현금 회수 배수", "1.0x"),
        ("RVPI", f"{summary['펀드 RVPI']}x", "잔존 미실현 가치", "-"),
        ("TVPI", f"{summary['펀드 TVPI']}x", "DPI + RVPI", "2.0x"),
    ]
    _table_header(pdf, f, ["Metric", "Value", "Description", "BM"], [24, 20, 90, 32])
    for i, r in enumerate(rows_ps):
        _table_row(pdf, f, list(r), [24, 20, 90, 32], shade=(i % 2 == 0))
    pdf.ln(8)

    # ── 2. 포트폴리오 상세 ──
    _section_header(pdf, f, "2. Portfolio Detail")
    _table_header(pdf, f, ["Company","Sector","Stage","Inv(M)","MOIC","IRR","DPI","RVPI","TVPI"],
                  [28,20,16,20,16,16,16,16,18])
    for i, r in result_df.iterrows():
        _table_row(pdf, f, [r["회사명"],r["섹터"],r["투자단계"],f"{int(r['투자금액_백만원']):,}",
                   f"{r['MOIC']}x",f"{r['IRR(%)']}%",f"{r['DPI']}x",f"{r['RVPI']}x",f"{r['TVPI']}x"],
                   [28,20,16,20,16,16,16,16,18], shade=(i%2==0))

    # ── 3. Top / Bottom Performers ──
    pdf.add_page()
    pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
    _section_header(pdf, f, "3. Top / Bottom Performers")
    sorted_r = result_df.sort_values("MOIC", ascending=False)
    top3 = sorted_r.head(3)
    bottom3 = sorted_r.tail(3)

    pdf.set_font(f, size=10)
    pdf.set_text_color(*_GREEN)
    pdf.cell(0, 6, "  Top Performers", ln=True)
    pdf.set_text_color(*_BLACK)
    _table_header(pdf, f, ["Rank","Company","Sector","MOIC","IRR"], [16,40,30,30,30])
    for i, (_, r) in enumerate(top3.iterrows()):
        _table_row(pdf, f, [str(i+1),r["회사명"],r["섹터"],f"{r['MOIC']}x",f"{r['IRR(%)']}%"],
                   [16,40,30,30,30], shade=(i%2==0))
    pdf.ln(6)

    pdf.set_font(f, size=10)
    pdf.set_text_color(198, 40, 40)
    pdf.cell(0, 6, "  Underperformers", ln=True)
    pdf.set_text_color(*_BLACK)
    _table_header(pdf, f, ["Rank","Company","Sector","MOIC","IRR"], [16,40,30,30,30])
    for i, (_, r) in enumerate(bottom3.iterrows()):
        _table_row(pdf, f, [str(i+1),r["회사명"],r["섹터"],f"{r['MOIC']}x",f"{r['IRR(%)']}%"],
                   [16,40,30,30,30], shade=(i%2==0))
    pdf.ln(8)

    # ── 4. 섹터 분석 ──
    _section_header(pdf, f, "4. Sector Analysis")
    sa = df_raw.groupby("섹터").agg(
        기업수=("회사명","count"), 총투자=("투자금액_백만원","sum")
    ).sort_values("총투자", ascending=False).reset_index()
    ti = sa["총투자"].sum()
    _table_header(pdf, f, ["Sector","Companies","Investment(M)","Weight"], [40,30,40,40])
    for i, (_, r) in enumerate(sa.iterrows()):
        pct = r["총투자"]/ti*100 if ti > 0 else 0
        _table_row(pdf, f, [r["섹터"],str(int(r["기업수"])),f"{int(r['총투자']):,}",f"{pct:.1f}%"],
                   [40,30,40,40], shade=(i%2==0))
    pdf.ln(8)

    # ── 5. Portfolio Analytics ──
    _section_header(pdf, f, "5. Portfolio Analytics")
    weights = df_raw["투자금액_백만원"] / df_raw["투자금액_백만원"].sum()
    hhi = round((weights ** 2).sum() * 10000)
    hhi_label = "High Risk" if hhi > 2500 else ("Medium" if hhi > 1500 else "Low (Diversified)")

    avg_days = (pd.to_datetime(df_raw["기준일"]) - pd.to_datetime(df_raw["투자일"])).dt.days.mean()
    avg_years = round(avg_days / 365.25, 1)
    total_val = df_raw["현재가치_백만원"].sum() + df_raw["회수금액_백만원"].sum()
    real_pct = round(df_raw["회수금액_백만원"].sum() / total_val * 100, 1) if total_val > 0 else 0

    pdf.set_font(f, size=9)
    for lab, val in [
        ("HHI Index (Concentration)", f"{hhi:,} - {hhi_label}"),
        ("Avg Holding Period", f"{avg_years} years"),
        ("Realization Rate", f"{real_pct}%"),
        ("Number of Sectors", f"{len(sa)}"),
        ("Total Invested", f"{int(ti):,}M"),
    ]:
        pdf.cell(60, 6, f"  {lab}")
        pdf.cell(0, 6, val, ln=True)
    pdf.ln(8)

    # ── 6. Risk Assessment ──
    _section_header(pdf, f, "6. Risk Assessment")
    pdf.set_font(f, size=9)
    under = result_df[result_df["MOIC"] < 1.0]
    if len(under) > 0:
        names = ", ".join(under["회사명"].tolist())
        pdf.set_text_color(198, 40, 40)
        pdf.cell(0, 6, f"  [HIGH] MOIC 1.0x 미만: {len(under)}개사 ({names})", ln=True)
    if hhi > 2500:
        pdf.set_text_color(198, 40, 40)
        pdf.cell(0, 6, f"  [HIGH] 포트폴리오 집중 리스크 (HHI {hhi:,})", ln=True)
    elif hhi > 1500:
        pdf.set_text_color(255, 152, 0)
        pdf.cell(0, 6, f"  [MEDIUM] 집중도 보통 (HHI {hhi:,}) - 분산 검토 필요", ln=True)
    if summary["펀드 DPI"] < 0.5:
        pdf.set_text_color(255, 152, 0)
        pdf.cell(0, 6, f"  [MEDIUM] 현금 회수 제한적 (DPI {summary['펀드 DPI']}x)", ln=True)
    if summary["펀드 MOIC"] >= 2.0:
        pdf.set_text_color(*_GREEN)
        pdf.cell(0, 6, f"  [POSITIVE] 우수 성과 (MOIC {summary['펀드 MOIC']}x, BM 2.0x 달성)", ln=True)
    if avg_irr > 15:
        pdf.set_text_color(*_GREEN)
        pdf.cell(0, 6, f"  [POSITIVE] 목표 IRR 달성 ({avg_irr}%, target 15%)", ln=True)
    pdf.set_text_color(*_BLACK)
    pdf.ln(8)

    # ── 7. AI Commentary ──
    _section_header(pdf, f, "7. AI Commentary")
    _commentary_block(pdf, f, commentary)

    # ── 8. J-Curve (있으면) ──
    if jcurve_df is not None and not jcurve_df.empty:
        pdf.add_page()
        pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
        _section_header(pdf, f, "8. J-Curve Analysis")
        pdf.set_font(f, size=9)
        mn = jcurve_df["누적현금흐름"].min()
        cr = jcurve_df["누적현금흐름"].iloc[-1]
        be = jcurve_df[jcurve_df["누적현금흐름"] >= 0]
        be_dt = str(be["날짜"].iloc[0]) if not be.empty else "Not reached"
        for lb, vl in [("Max Drawdown", f"{mn:,.0f}M"),("Current CF", f"{cr:,.0f}M"),("Break-even", be_dt)]:
            pdf.cell(50, 6, f"  {lb}"); pdf.cell(0, 6, vl, ln=True)
        pdf.ln(3)
        if jcurve_comment:
            _commentary_block(pdf, f, jcurve_comment)

    # ── 9. 분기별 추이 (있으면) ──
    if trend_df is not None and not trend_df.empty:
        _section_header(pdf, f, "9. Quarterly Trend")
        cols = list(trend_df.columns)
        cw = 166 // len(cols)
        _table_header(pdf, f, cols, [cw]*len(cols))
        for i, r in trend_df.iterrows():
            _table_row(pdf, f, [str(r[c]) for c in cols], [cw]*len(cols), shade=(i%2==0))
        pdf.ln(4)
        if trend_comment:
            _commentary_block(pdf, f, trend_comment)

    # ── 10. 거시지표 (있으면) ──
    if rate_df is not None or fx_df is not None:
        pdf.add_page()
        pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
        _section_header(pdf, f, "10. Macro Indicators")
        pdf.set_font(f, size=9)
        if rate_df is not None and not rate_df.empty:
            pdf.cell(0, 6, f"  Base Rate: {rate_df['기준금리(%)'].iloc[-1]}%", ln=True)
        if fx_df is not None and not fx_df.empty:
            pdf.cell(0, 6, f"  KRW/USD: {fx_df['원/달러(원)'].iloc[-1]:,.0f}", ln=True)
        if spread is not None:
            pdf.cell(0, 6, f"  Fund IRR vs Base Rate Spread: {spread:+.1f}%p", ln=True)
        pdf.ln(3)
        if macro_comment:
            _commentary_block(pdf, f, macro_comment)

    # ── 면책 조항 ──
    pdf.add_page()
    pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
    _section_header(pdf, f, "Disclaimer")
    pdf.set_font(f, size=8)
    pdf.set_text_color(*_GREY)
    disclaimer = (
        "본 보고서는 PE/VC 분기 보고 도우미 시스템에 의해 자동 생성된 참고 자료입니다. "
        "본 자료는 투자 권유, 투자 자문, 또는 투자 결정의 근거로 사용될 수 없으며, "
        "보고서에 포함된 수치와 분석은 입력된 데이터 및 외부 API 조회 결과에 기반한 추정치입니다. "
        "실제 투자 의사결정 시에는 반드시 별도의 전문가 검증 및 실사(Due Diligence)를 수행하시기 바랍니다. "
        "AI 코멘터리는 Claude API를 통해 자동 생성된 것으로, 정보의 정확성을 보장하지 않습니다. "
        "DART, ECOS, KVIC 등 외부 API 데이터의 실시간성 및 정확성은 해당 기관의 제공 기준에 따릅니다."
    )
    pdf.multi_cell(0, 5, disclaimer)
    pdf.set_text_color(*_BLACK)

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
