import os
import tempfile
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


_CHART_STYLE = dict(
    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
    font=dict(family="sans-serif", size=11, color="#333"),
    margin=dict(t=35, b=25, l=50, r=20),
)

def _style_chart(fig, title="", h=300):
    fig.update_layout(**_CHART_STYLE, height=h, showlegend=True,
                      legend=dict(orientation="h", y=-0.15, font_size=10, bgcolor="rgba(0,0,0,0)"))
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=13, color="#1a1a1a"), x=0.02, y=0.97))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", gridwidth=0.5, zeroline=False)
    return fig


def _render_chart(fig, width=170, height=100) -> str | None:
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.write_image(tmp.name, width=width*4, height=height*4, scale=2, engine="kaleido")
        return tmp.name
    except Exception:
        return None


def _add_chart(pdf: FPDF, fig, w=170, h=90):
    path = _render_chart(fig, w, h)
    if path:
        pdf.image(path, x=20, w=w)
        pdf.ln(3)
        try:
            os.unlink(path)
        except Exception:
            pass


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
    include_waterfall=False, include_scenario=False,
    scenario_company="", scenario_df=None, scenario_opt=None,
    selected_sections=None,
    sensitivity_df=None, sensitivity_company="",
    dart_fin_df=None, dart_company="",
    include_charts=False,
):
    pdf = _new_pdf()
    f = _font(pdf)
    import numpy as np

    sel = set(selected_sections) if selected_sections else set()
    sec_num = [0]
    def _next_sec():
        sec_num[0] += 1
        return sec_num[0]

    _cover_page(pdf, f, "Quarterly Report", f"분기 보고서 (참고용)  ·  {quarter}",
                fund_name, fund_strategy, quarter, base_date)

    avg_irr = round(result_df["IRR(%)"].mean(), 1)
    need_page = [True]

    def _ensure_page():
        if need_page[0]:
            pdf.add_page()
            pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
            need_page[0] = False

    def _new_page():
        pdf.add_page()
        pdf.set_fill_color(*_BG); pdf.rect(0, 0, 210, 297, "F")
        need_page[0] = False

    # ── 성과 요약 ──
    if any("성과 요약" in s for s in sel):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Performance Summary")
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
        pdf.ln(4)

        if include_charts:
            import plotly.graph_objects as go
            sorted_r = result_df.sort_values("MOIC", ascending=True)
            colors = ["#1b5e20" if m >= 2 else "#43a047" if m >= 1.5 else "#66bb6a" if m >= 1 else "#ef5350" for m in sorted_r["MOIC"]]
            fig_moic = go.Figure(go.Bar(
                x=sorted_r["MOIC"].tolist(), y=sorted_r["회사명"].tolist(),
                orientation="h", marker_color=colors, marker_line_width=0,
                text=[f"{m}x" for m in sorted_r["MOIC"]], textposition="outside",
                textfont=dict(size=11, color="#333"),
            ))
            fig_moic.add_vline(x=2.0, line_dash="dot", line_color="#bbb", annotation_text="BM 2.0x",
                               annotation_font_size=9, annotation_font_color="#999")
            _style_chart(fig_moic, "Portfolio MOIC", h=300)
            fig_moic.update_layout(margin=dict(t=35, b=15, l=90, r=40), bargap=0.35)
            fig_moic.update_yaxes(showgrid=False)
            _add_chart(pdf, fig_moic, w=170, h=75)
        pdf.ln(2)

    # ── 포트폴리오 상세 ──
    if any("포트폴리오 상세" in s for s in sel):
        _ensure_page() if sec_num[0] > 0 else _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Portfolio Detail")
        _table_header(pdf, f, ["Company","Sector","Stage","Inv(M)","MOIC","IRR","DPI","RVPI","TVPI"],
                      [28,20,16,20,16,16,16,16,18])
        for i, r in result_df.iterrows():
            _table_row(pdf, f, [r["회사명"],r["섹터"],r["투자단계"],f"{int(r['투자금액_백만원']):,}",
                       f"{r['MOIC']}x",f"{r['IRR(%)']}%",f"{r['DPI']}x",f"{r['RVPI']}x",f"{r['TVPI']}x"],
                       [28,20,16,20,16,16,16,16,18], shade=(i%2==0))

    # ── Top / Bottom Performers ──
    if any("Top/Bottom" in s for s in sel):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Top / Bottom Performers")
        sorted_r = result_df.sort_values("MOIC", ascending=False)
        top3 = sorted_r.head(3)
        bottom3 = sorted_r.tail(3)

        if include_charts:
            import plotly.graph_objects as go
            tb = pd.concat([top3, bottom3]).sort_values("MOIC", ascending=True)
            colors = ["#1b5e20" if m >= 2 else "#43a047" if m >= 1 else "#ef5350" for m in tb["MOIC"]]
            fig_tb = go.Figure()
            fig_tb.add_trace(go.Bar(
                x=tb["MOIC"].tolist(), y=[f"{r['회사명']} ({r['섹터']})" for _, r in tb.iterrows()],
                orientation="h", marker_color=colors, marker_line_width=0,
                text=[f"{m}x · IRR {irr}%" for m, irr in zip(tb["MOIC"], tb["IRR(%)"])],
                textposition="outside", textfont=dict(size=10),
            ))
            _style_chart(fig_tb, "Top & Bottom MOIC", h=280)
            fig_tb.update_layout(margin=dict(t=35, b=15, l=120, r=60), showlegend=False, bargap=0.3)
            fig_tb.update_xaxes(showgrid=True, title="MOIC")
            fig_tb.update_yaxes(showgrid=False)
            _add_chart(pdf, fig_tb, w=170, h=70)
        else:
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
        pdf.ln(4)

    # ── 섹터 분석 ──
    if any("섹터" in s for s in sel):
        _new_page()
        sa = df_raw.groupby("섹터").agg(
            기업수=("회사명","count"), 총투자=("투자금액_백만원","sum")
        ).sort_values("총투자", ascending=False).reset_index()
        ti = sa["총투자"].sum()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Sector Analysis")
        _table_header(pdf, f, ["Sector","Companies","Investment(M)","Weight"], [40,30,40,40])
        for i, (_, r) in enumerate(sa.iterrows()):
            pct = r["총투자"]/ti*100 if ti > 0 else 0
            _table_row(pdf, f, [r["섹터"],str(int(r["기업수"])),f"{int(r['총투자']):,}",f"{pct:.1f}%"],
                       [40,30,40,40], shade=(i%2==0))
        pdf.ln(4)

        if include_charts:
            import plotly.graph_objects as go
            fig_pie = go.Figure(go.Pie(
                labels=sa["섹터"].tolist(), values=sa["총투자"].tolist(),
                marker=dict(colors=["#1b5e20","#2e7d32","#43a047","#66bb6a","#81c784","#a5d6a7","#c8e6c9","#e8f5e9"],
                            line=dict(color="#ffffff", width=2)),
                textinfo="label+percent", textfont=dict(size=11),
                hole=0.35,
            ))
            _style_chart(fig_pie, "Sector Allocation", h=300)
            fig_pie.update_layout(margin=dict(t=35, b=10, l=10, r=10), showlegend=False)
            _add_chart(pdf, fig_pie, w=150, h=75)
        pdf.ln(2)

    # ── 집중도·투자기간·실현율 ──
    if any("집중도" in s for s in sel):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Portfolio Analytics")
        weights = df_raw["투자금액_백만원"] / df_raw["투자금액_백만원"].sum()
        hhi = round((weights ** 2).sum() * 10000)
        hhi_label = "High Risk" if hhi > 2500 else ("Medium" if hhi > 1500 else "Low (Diversified)")
        avg_days = (pd.to_datetime(df_raw["기준일"]) - pd.to_datetime(df_raw["투자일"])).dt.days.mean()
        avg_years = round(avg_days / 365.25, 1)
        total_val = df_raw["현재가치_백만원"].sum() + df_raw["회수금액_백만원"].sum()
        real_pct = round(df_raw["회수금액_백만원"].sum() / total_val * 100, 1) if total_val > 0 else 0
        sa2 = df_raw.groupby("섹터").agg(기업수=("회사명","count")).reset_index()
        ti2 = df_raw["투자금액_백만원"].sum()
        pdf.set_font(f, size=9)
        for lab, val in [
            ("HHI Index (Concentration)", f"{hhi:,} - {hhi_label}"),
            ("Avg Holding Period", f"{avg_years} years"),
            ("Realization Rate", f"{real_pct}%"),
            ("Number of Sectors", f"{len(sa2)}"),
            ("Total Invested", f"{int(ti2):,}M"),
        ]:
            pdf.cell(60, 6, f"  {lab}")
            pdf.cell(0, 6, val, ln=True)
        pdf.ln(8)

    # ── 리스크 평가 ──
    if any("리스크" in s for s in sel):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Risk Assessment")
        pdf.set_font(f, size=9)
        weights_r = df_raw["투자금액_백만원"] / df_raw["투자금액_백만원"].sum()
        hhi_r = round((weights_r ** 2).sum() * 10000)
        under = result_df[result_df["MOIC"] < 1.0]
        if len(under) > 0:
            names = ", ".join(under["회사명"].tolist())
            pdf.set_text_color(198, 40, 40)
            pdf.cell(0, 6, f"  [HIGH] MOIC 1.0x 미만: {len(under)}개사 ({names})", ln=True)
        if hhi_r > 2500:
            pdf.set_text_color(198, 40, 40)
            pdf.cell(0, 6, f"  [HIGH] 포트폴리오 집중 리스크 (HHI {hhi_r:,})", ln=True)
        elif hhi_r > 1500:
            pdf.set_text_color(255, 152, 0)
            pdf.cell(0, 6, f"  [MEDIUM] 집중도 보통 (HHI {hhi_r:,}) - 분산 검토 필요", ln=True)
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

    # ── AI Commentary ──
    if any("AI" in s for s in sel) and commentary:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. AI Commentary")
        _commentary_block(pdf, f, commentary)

    # ── J-Curve ──
    if any("J-Curve" in s for s in sel) and jcurve_df is not None and not jcurve_df.empty:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. J-Curve Analysis")
        pdf.set_font(f, size=9)
        mn = jcurve_df["누적현금흐름"].min()
        cr = jcurve_df["누적현금흐름"].iloc[-1]
        be = jcurve_df[jcurve_df["누적현금흐름"] >= 0]
        be_dt = str(be["날짜"].iloc[0]) if not be.empty else "Not reached"
        for lb, vl in [("Max Drawdown", f"{mn:,.0f}M"),("Current CF", f"{cr:,.0f}M"),("Break-even", be_dt)]:
            pdf.cell(50, 6, f"  {lb}"); pdf.cell(0, 6, vl, ln=True)
        pdf.ln(3)

        if include_charts:
            import plotly.graph_objects as go
            dates = jcurve_df["날짜"].astype(str).tolist()
            cf = jcurve_df["누적현금흐름"].tolist()
            colors = ["#1b5e20" if v >= 0 else "#ef5350" for v in cf]
            fig_jc = go.Figure()
            fig_jc.add_trace(go.Scatter(
                x=dates, y=cf, mode="lines+markers",
                line=dict(color="#1b5e20", width=2.5),
                marker=dict(size=6, color=colors, line=dict(width=1, color="#ffffff")),
                fill="tozeroy", fillcolor="rgba(27,94,32,0.08)",
            ))
            fig_jc.add_hline(y=0, line_dash="dash", line_color="#999", line_width=1)
            _style_chart(fig_jc, "J-Curve — Cumulative Cash Flow", h=300)
            fig_jc.update_layout(showlegend=False, margin=dict(t=35, b=30, l=60, r=20))
            fig_jc.update_yaxes(title="백만원")
            _add_chart(pdf, fig_jc, w=170, h=75)
            pdf.ln(2)

        if jcurve_comment:
            _commentary_block(pdf, f, jcurve_comment)

    # ── 분기별 추이 ──
    if any("분기별" in s for s in sel) and trend_df is not None and not trend_df.empty:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Quarterly Trend")
        cols = list(trend_df.columns)
        cw = 166 // len(cols)
        _table_header(pdf, f, cols, [cw]*len(cols))
        for i, r in trend_df.iterrows():
            _table_row(pdf, f, [str(r[c]) for c in cols], [cw]*len(cols), shade=(i%2==0))
        pdf.ln(4)
        if trend_comment:
            _commentary_block(pdf, f, trend_comment)

    # ── 거시지표 ──
    if any("거시" in s for s in sel) and (rate_df is not None or fx_df is not None):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Macro Indicators")
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

    # ── Waterfall ──
    if any("Waterfall" in s for s in sel):
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Waterfall Distribution")
        wf_inv = float(df_raw["투자금액_백만원"].sum())
        wf_proc = float(df_raw["현재가치_백만원"].sum() + df_raw["회수금액_백만원"].sum())
        hurdle, carry, years = 8, 20, 5
        profit = max(0, wf_proc - wf_inv)
        hurdle_amt = wf_inv * ((1 + hurdle/100)**years - 1)
        rem = wf_proc
        s1 = min(rem, wf_inv); rem -= s1
        s2 = min(rem, hurdle_amt); rem -= s2
        gp_target = profit * carry / 100
        s3_gp = min(rem, gp_target); rem -= s3_gp
        s4_gp = rem * carry / 100; s4_lp = rem - s4_gp
        total_lp = s1 + s2 + s4_lp; total_gp = s3_gp + s4_gp

        lp_moic = total_lp / wf_inv if wf_inv > 0 else 0
        eff_carry = total_gp / profit * 100 if profit > 0 else 0

        if include_charts:
            import plotly.graph_objects as go
            labels = ["① 원금 반환", "② 우선수익", "③ GP Catch-up", "④ Carry Split"]
            lp_vals = [s1, s2, 0, s4_lp]
            gp_vals = [0, 0, s3_gp, s4_gp]
            fig_wf = go.Figure()
            fig_wf.add_trace(go.Bar(name="LP", x=labels, y=lp_vals,
                                    marker_color="#1b5e20", marker_line_width=0,
                                    text=[f"{v:,.0f}" for v in lp_vals], textposition="inside",
                                    textfont=dict(color="#fff", size=11)))
            fig_wf.add_trace(go.Bar(name="GP", x=labels, y=gp_vals,
                                    marker_color="#a5d6a7", marker_line_width=0,
                                    text=[f"{v:,.0f}" if v > 0 else "" for v in gp_vals], textposition="inside",
                                    textfont=dict(color="#1a1a1a", size=11)))
            _style_chart(fig_wf, f"Waterfall — LP {total_lp:,.0f}M ({lp_moic:.2f}x) / GP {total_gp:,.0f}M", h=300)
            fig_wf.update_layout(barmode="stack", bargap=0.3)
            fig_wf.update_yaxes(title="백만원")
            _add_chart(pdf, fig_wf, w=170, h=75)
        else:
            pdf.set_font(f, size=9)
            pdf.cell(0, 6, f"  Params: Invested {wf_inv:,.0f}M | Proceeds {wf_proc:,.0f}M | Hurdle {hurdle}% | Carry {carry}% | {years}yr", ln=True)
            pdf.ln(3)
            steps = [
                ("1. Return of Capital", f"LP <- {s1:,.0f}M"),
                ("2. Preferred Return", f"LP <- {s2:,.0f}M (Hurdle {hurdle}% x {years}yr)"),
                ("3. GP Catch-up", f"GP <- {s3_gp:,.0f}M"),
                ("4. Carry Split", f"LP {s4_lp:,.0f}M / GP {s4_gp:,.0f}M"),
            ]
            _table_header(pdf, f, ["Step", "Distribution"], [60, 90])
            for i, (step, dist) in enumerate(steps):
                _table_row(pdf, f, [step, dist], [60, 90], shade=(i%2==0))
            pdf.ln(4)
            pdf.set_font(f, size=9)
            pdf.cell(0, 6, f"  Result: LP {total_lp:,.0f}M (MOIC {lp_moic:.2f}x) | GP {total_gp:,.0f}M (Eff.Carry {eff_carry:.1f}%)", ln=True)

    # ── 시나리오 ──
    if any("시나리오" in s for s in sel) and scenario_df is not None:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. Exit Scenario — {scenario_company}")

        if include_charts and "Exit 배수" in scenario_df.columns and "IRR (%)" in scenario_df.columns:
            import plotly.express as px
            fig_sc = px.bar(scenario_df, x="Exit 배수", y="IRR (%)",
                            color="IRR (%)", color_continuous_scale=["#e8f5e9","#66bb6a","#2e7d32","#1b5e20"],
                            text="IRR (%)")
            fig_sc.update_traces(texttemplate="%{text}%", textposition="outside", marker_line_width=0)
            _style_chart(fig_sc, f"Exit Scenario — {scenario_company}", h=280)
            fig_sc.update_layout(showlegend=False, bargap=0.3)
            _add_chart(pdf, fig_sc, w=170, h=70)
            pdf.ln(2)

        cols = list(scenario_df.columns)
        cw = 166 // max(len(cols), 1)
        _table_header(pdf, f, cols, [cw]*len(cols))
        for i, row in scenario_df.iterrows():
            _table_row(pdf, f, [str(row[c]) for c in cols], [cw]*len(cols), shade=(i%2==0))
        pdf.ln(4)
        if scenario_opt:
            pdf.set_font(f, size=9)
            for k, v in scenario_opt.items():
                pdf.cell(0, 6, f"  {k}: {v}", ln=True)

    # ── IRR Sensitivity ──
    if any("Sensitivity" in s for s in sel) and sensitivity_df is not None:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. IRR Sensitivity Matrix — {sensitivity_company}")

        if include_charts:
            import plotly.graph_objects as go
            matrix = sensitivity_df.values.tolist()
            fig_heat = go.Figure(data=go.Heatmap(
                z=matrix, x=list(sensitivity_df.columns), y=list(sensitivity_df.index),
                colorscale=[[0,"#d32f2f"],[0.15,"#e53935"],[0.3,"#ff9800"],[0.45,"#ffc107"],
                            [0.55,"#cddc39"],[0.7,"#66bb6a"],[0.85,"#43a047"],[1.0,"#1b5e20"]],
                zmid=15, text=[[f"{v}%" for v in row] for row in matrix],
                texttemplate="%{text}", textfont=dict(size=9, color="#ffffff"),
            ))
            _style_chart(fig_heat, f"IRR Sensitivity — {sensitivity_company}", h=350)
            fig_heat.update_layout(margin=dict(t=35, b=30, l=50, r=10))
            fig_heat.update_xaxes(title="보유기간")
            fig_heat.update_yaxes(title="Exit 배수", showgrid=False)
            _add_chart(pdf, fig_heat, w=170, h=85)
        else:
            idx_col = "Exit 배수"
            cols = list(sensitivity_df.columns)
            all_cols = [idx_col] + cols
            cw = 166 // max(len(all_cols), 1)
            _table_header(pdf, f, all_cols, [cw]*len(all_cols))
            for j, (idx, row) in enumerate(sensitivity_df.iterrows()):
                _table_row(pdf, f, [str(idx)] + [str(row[c]) for c in cols], [cw]*len(all_cols), shade=(j%2==0))

    # ── DART 재무 ──
    if any("DART" in s for s in sel) and dart_fin_df is not None:
        _new_page()
        n = _next_sec()
        _section_header(pdf, f, f"{n}. DART Financials — {dart_company}")
        cols = list(dart_fin_df.columns)
        cw = 166 // max(len(cols), 1)
        _table_header(pdf, f, cols, [cw]*len(cols))
        for i, row in dart_fin_df.iterrows():
            vals = []
            for c in cols:
                v = row[c]
                if isinstance(v, (int, float)) and c != "연도":
                    vals.append(f"{int(v):,}" if pd.notna(v) else "-")
                else:
                    vals.append(str(v))
            _table_row(pdf, f, vals, [cw]*len(cols), shade=(i%2==0))

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
