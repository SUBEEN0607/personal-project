"""
LP 보고서 PPTX 생성 모듈 — 선택 섹션 + 차트 이미지 지원
"""
import io
import os
import tempfile
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ── 팔레트 ──
D_GREEN  = RGBColor(0x1b, 0x5e, 0x20)
M_GREEN  = RGBColor(0x2e, 0x7d, 0x32)
GREEN    = RGBColor(0x43, 0xa0, 0x47)
L_GREEN  = RGBColor(0xa5, 0xd6, 0xa7)
P_GREEN  = RGBColor(0xc8, 0xe6, 0xc9)
XP_GREEN = RGBColor(0xe8, 0xf5, 0xe9)
BLACK    = RGBColor(0x1a, 0x1a, 0x1a)
D_GREY   = RGBColor(0x55, 0x55, 0x55)
GREY     = RGBColor(0x99, 0x99, 0x99)
L_GREY   = RGBColor(0xCC, 0xCC, 0xCC)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
BG       = RGBColor(0xFA, 0xFA, 0xF8)
BORDER   = RGBColor(0xEA, 0xE8, 0xE4)
RED_SOFT = RGBColor(0xC6, 0x28, 0x28)

FONT = "맑은 고딕"
W = Inches(13.333)
H = Inches(7.5)

# ── 헬퍼 ──
def _bg(slide, color=BG):
    fill = slide.background.fill; fill.solid(); fill.fore_color.rgb = color

def _rect(s, l, t, w, h, c, border=None):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    r.fill.solid(); r.fill.fore_color.rgb = c
    if border: r.line.color.rgb = border; r.line.width = Pt(1)
    else: r.line.fill.background()
    return r

def _rounded(s, l, t, w, h, c=WHITE, border=BORDER):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    r.fill.solid(); r.fill.fore_color.rgb = c
    r.line.color.rgb = border; r.line.width = Pt(1); r.adjustments[0] = 0.04
    return r

def _circle(s, l, t, size, c=D_GREEN):
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, l, t, size, size)
    o.fill.solid(); o.fill.fore_color.rgb = c; o.line.fill.background()

def _text(s, l, t, w, h, txt, sz=14, c=BLACK, bold=False, align=PP_ALIGN.LEFT):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = str(txt)
    p.font.size = Pt(sz); p.font.color.rgb = c; p.font.bold = bold
    p.font.name = FONT; p.alignment = align; p.space_after = Pt(0)
    return tb

def _multi(s, l, t, w, h, lines, sz=12, c=BLACK, spacing=6):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = str(line); p.font.size = Pt(sz); p.font.color.rgb = c
        p.font.name = FONT; p.space_after = Pt(spacing)
    return tb

def _circle_num(s, l, t, txt, bg=D_GREEN, fg=WHITE):
    _circle(s, l, t, Inches(0.4), bg)
    _text(s, l, t, Inches(0.4), Inches(0.4), txt, sz=11, c=fg, bold=True, align=PP_ALIGN.CENTER)

def _header(s, label, title):
    _text(s, Inches(0.8), Inches(0.35), Inches(6), Inches(0.2), label, sz=9, c=GREY, bold=True)
    _text(s, Inches(0.8), Inches(0.6), Inches(11), Inches(0.5), title, sz=26, c=BLACK, bold=True)
    _rect(s, Inches(0.8), Inches(1.15), Inches(0.6), Pt(3), D_GREEN)
    _rect(s, Inches(1.5), Inches(1.15), Inches(11), Pt(1), BORDER)

def _page(s, n, total):
    _text(s, Inches(12.0), Inches(7.05), Inches(1.2), Inches(0.3),
          f"{n}/{total}", sz=8, c=L_GREY, align=PP_ALIGN.RIGHT)

def _metric_card(s, l, t, w, h, label, value, sub="", bg=WHITE, val_color=D_GREEN):
    _rounded(s, l, t, w, h, bg, BORDER)
    _text(s, l, t + Inches(0.15), w, Inches(0.2), label, sz=9, c=GREY, bold=True, align=PP_ALIGN.CENTER)
    _text(s, l, t + Inches(0.45), w, Inches(0.5), value, sz=30, c=val_color, bold=True, align=PP_ALIGN.CENTER)
    if sub:
        _text(s, l, t + Inches(1.0), w, Inches(0.2), sub, sz=8, c=GREY, align=PP_ALIGN.CENTER)

def _bar_visual(s, l, t, w, h, pct, color=D_GREEN, bg=P_GREEN):
    _rounded(s, l, t, w, h, bg, bg)
    fill_w = max(int(w * min(pct, 1.0)), Inches(0.05))
    _rect(s, l, t, fill_w, h, color)

def _add_chart_to_slide(s, fig, left, top, width_in, height_in):
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.write_image(tmp.name, width=width_in*100, height=height_in*100, scale=2, engine="kaleido")
        s.shapes.add_picture(tmp.name, Inches(left), Inches(top), Inches(width_in))
        os.unlink(tmp.name)
    except Exception:
        pass


# ══════════════════════════════════════════════════
def generate_lp_pptx(
    summary: dict,
    result_df: pd.DataFrame,
    commentary: str,
    quarter: str = "",
    fund_name: str = "PE/VC 펀드",
    fund_strategy: str = "VC",
    base_date: str = "",
    selected_sections: list = None,
    include_charts: bool = False,
    jcurve_df=None,
    scenario_df=None, scenario_company: str = "",
) -> bytes:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    sel = set(selected_sections) if selected_sections else set()
    include_all = len(sel) == 0
    def _sec(keyword):
        return include_all or any(keyword in s for s in sel)

    moic = summary["펀드 MOIC"]
    dpi = summary["펀드 DPI"]
    rvpi = summary["펀드 RVPI"]
    tvpi = summary["펀드 TVPI"]
    avg_irr = round(result_df["IRR(%)"].mean(), 1)
    n = summary["포트폴리오사 수"]
    total_inv = summary["총 투자금액 (백만원)"]
    colors = [D_GREEN, M_GREEN, GREEN, L_GREEN, D_GREEN, M_GREEN, GREEN, L_GREEN]

    slides = []

    # ═══ 1. 표지 (항상) ═══
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, D_GREEN)
    _img_path = ""
    for _p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "skku_wallpaper.jpg"),
        os.path.join(os.getcwd(), "skku_wallpaper.jpg"),
    ]:
        if os.path.exists(_p): _img_path = _p; break
    if _img_path:
        s.shapes.add_picture(_img_path, Inches(0), Inches(0), W, H)
    overlay = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), W, H)
    overlay.fill.solid(); overlay.fill.fore_color.rgb = RGBColor(0x10, 0x30, 0x12)
    overlay.line.fill.background()
    try:
        a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
        fill_elem = overlay._element.find(f'.//{{{a_ns}}}solidFill')
        if fill_elem is not None:
            from lxml import etree
            alpha_elem = etree.SubElement(fill_elem[0], f'{{{a_ns}}}alpha')
            alpha_elem.set('val', '45000')
    except Exception:
        pass
    _text(s, Inches(1.2), Inches(1.3), Inches(8), Inches(0.2), "QUARTERLY PORTFOLIO REPORT", sz=10, c=L_GREEN, bold=True)
    _rect(s, Inches(1.2), Inches(1.7), Inches(0.8), Pt(3), L_GREEN)
    _text(s, Inches(1.2), Inches(2.0), Inches(8), Inches(0.8), fund_name, sz=44, c=WHITE, bold=True)
    _text(s, Inches(1.2), Inches(3.2), Inches(8), Inches(0.4), f"{fund_strategy}  ·  {quarter}  ·  {base_date}", sz=16, c=P_GREEN)
    for i, (lab, val) in enumerate([("MOIC", f"{moic}x"), ("IRR", f"{avg_irr}%"), ("TVPI", f"{tvpi}x"), ("Portfolio", f"{n}개사")]):
        x = Inches(1.2) + Inches(i * 2.2)
        _text(s, x, Inches(5.0), Inches(2), Inches(0.2), lab, sz=9, c=L_GREEN)
        _text(s, x, Inches(5.3), Inches(2), Inches(0.4), val, sz=22, c=WHITE, bold=True)
    _text(s, Inches(1.2), Inches(6.3), Inches(8), Inches(0.2), "PE/VC 분기 보고 도우미  ·  SDIC", sz=10, c=L_GREEN)
    slides.append("표지")

    # ═══ 2. 성과 요약 ═══
    if _sec("성과 요약"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "PERFORMANCE SUMMARY", "성과 요약")
        _metric_card(s, Inches(0.8), Inches(1.5), Inches(5.7), Inches(1.5), "MOIC", f"{moic}x", "투자원금 대비 전체 가치 배수")
        _metric_card(s, Inches(6.8), Inches(1.5), Inches(5.7), Inches(1.5), "IRR", f"{avg_irr}%", "시간가치 반영 연환산 수익률")
        for i, (lab, val, sub) in enumerate([("DPI", f"{dpi}x", "현금 회수"), ("RVPI", f"{rvpi}x", "잔존 가치"), ("TVPI", f"{tvpi}x", "DPI+RVPI"), ("투자기업", f"{n}개", f"총 {total_inv:,}M")]):
            _metric_card(s, Inches(0.8)+Inches(i*3.05), Inches(3.4), Inches(2.8), Inches(1.3), lab, val, sub, bg=XP_GREEN, val_color=D_GREEN)
        for i, (nm, act, tgt, desc) in enumerate([("MOIC", moic, 2.0, "≥ 2.0x"), ("IRR", avg_irr, 15.0, "≥ 15%"), ("TVPI", tvpi, 2.0, "≥ 2.0x")]):
            y = Inches(5.3) + Inches(i * 0.55)
            _text(s, Inches(0.8), y, Inches(1.0), Inches(0.2), nm, sz=10, c=BLACK, bold=True)
            _bar_visual(s, Inches(2.0), y+Inches(0.02), Inches(7.5), Inches(0.2), min(float(act)/float(tgt), 1.5)/1.5)
            clr = D_GREEN if float(act) >= tgt else RED_SOFT
            _text(s, Inches(9.8), y, Inches(1.5), Inches(0.2), f"{act}/{tgt}", sz=9, c=clr, bold=True)
        slides.append("성과")

    # ═══ 3. 포트폴리오 상세 ═══
    if _sec("포트폴리오"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "PORTFOLIO DETAIL", "포트폴리오 상세")
        sorted_df = result_df.sort_values("MOIC", ascending=False).head(8)
        for i, (_, row) in enumerate(sorted_df.iterrows()):
            col = i % 4; r = i // 4
            x = Inches(0.5) + Inches(col * 3.15); y = Inches(1.5) + Inches(r * 2.8)
            clr = colors[i % len(colors)]
            _rounded(s, x, y, Inches(2.9), Inches(2.5), WHITE, BORDER)
            _circle_num(s, x+Inches(0.15), y+Inches(0.15), str(i+1), bg=clr)
            _text(s, x+Inches(0.65), y+Inches(0.18), Inches(2.0), Inches(0.25), row["회사명"], sz=13, c=BLACK, bold=True)
            _text(s, x+Inches(0.65), y+Inches(0.45), Inches(2.0), Inches(0.2), f'{row["섹터"]} · {row["투자단계"]}', sz=8, c=GREY)
            moic_val = float(row["MOIC"]); irr_val = float(row["IRR(%)"])
            _text(s, x+Inches(0.15), y+Inches(0.85), Inches(0.8), Inches(0.2), "MOIC", sz=8, c=GREY, bold=True)
            _text(s, x+Inches(1.8), y+Inches(0.85), Inches(0.9), Inches(0.2), f"{moic_val}x", sz=10, c=clr, bold=True, align=PP_ALIGN.RIGHT)
            _bar_visual(s, x+Inches(0.15), y+Inches(1.1), Inches(2.55), Inches(0.15), min(moic_val/5.0, 1.0), clr)
            _text(s, x+Inches(0.15), y+Inches(1.4), Inches(0.8), Inches(0.2), "IRR", sz=8, c=GREY, bold=True)
            _text(s, x+Inches(1.8), y+Inches(1.4), Inches(0.9), Inches(0.2), f"{irr_val}%", sz=10, c=clr, bold=True, align=PP_ALIGN.RIGHT)
            _bar_visual(s, x+Inches(0.15), y+Inches(1.65), Inches(2.55), Inches(0.15), min(max(irr_val,0)/50.0, 1.0), clr)
            _text(s, x+Inches(0.15), y+Inches(2.0), Inches(1.3), Inches(0.2), f'투자 {int(row["투자금액_백만원"]):,}M', sz=8, c=D_GREY)
            _text(s, x+Inches(1.5), y+Inches(2.0), Inches(1.2), Inches(0.2), f'TVPI {row["TVPI"]}x', sz=8, c=D_GREY, align=PP_ALIGN.RIGHT)
        slides.append("포트폴리오")

    # ═══ 4. 섹터 분석 ═══
    if _sec("섹터"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "SECTOR ANALYSIS", "섹터별 분석")
        if "섹터" in result_df.columns:
            sa = result_df.groupby("섹터").agg(기업수=("회사명","count"), 총투자=("투자금액_백만원","sum"), 평균MOIC=("MOIC","mean"), 평균IRR=("IRR(%)","mean")).sort_values("총투자", ascending=False).reset_index()
            total_all = sa["총투자"].sum()
            for i, (_, row) in enumerate(sa.head(8).iterrows()):
                y = Inches(1.5) + Inches(i * 0.6); clr = colors[i % len(colors)]
                _circle_num(s, Inches(0.8), y, str(i+1), bg=clr)
                _text(s, Inches(1.35), y+Inches(0.03), Inches(1.8), Inches(0.22), row["섹터"], sz=12, c=BLACK, bold=True)
                pct = float(row["총투자"])/total_all if total_all > 0 else 0
                _bar_visual(s, Inches(3.3), y+Inches(0.05), Inches(4.5), Inches(0.18), pct, clr)
                _text(s, Inches(8.0), y+Inches(0.03), Inches(0.8), Inches(0.22), f"{pct*100:.0f}%", sz=11, c=clr, bold=True)
                _text(s, Inches(9.0), y+Inches(0.03), Inches(1.0), Inches(0.22), f"{int(row['기업수'])}개사", sz=9, c=D_GREY)
                _text(s, Inches(10.1), y+Inches(0.03), Inches(1.2), Inches(0.22), f"MOIC {row['평균MOIC']:.1f}x", sz=9, c=D_GREY)
                _text(s, Inches(11.3), y+Inches(0.03), Inches(1.2), Inches(0.22), f"IRR {row['평균IRR']:.0f}%", sz=9, c=D_GREY)

        slides.append("섹터")

    # ═══ 5. Top/Bottom ═══
    if _sec("Top/Bottom"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "TOP / BOTTOM PERFORMERS", "성과 상위 · 하위 분석")
        sd = result_df.sort_values("MOIC", ascending=False)
        _text(s, Inches(0.8), Inches(1.5), Inches(5), Inches(0.3), "TOP PERFORMERS", sz=11, c=D_GREEN, bold=True)
        for i, (_, row) in enumerate(sd.head(3).iterrows()):
            y = Inches(1.9) + Inches(i * 0.7)
            _circle_num(s, Inches(0.8), y, str(i+1), bg=D_GREEN)
            _text(s, Inches(1.4), y+Inches(0.03), Inches(2.5), Inches(0.25), row["회사명"], sz=14, c=BLACK, bold=True)
            _text(s, Inches(4.0), y+Inches(0.03), Inches(1.5), Inches(0.25), f'MOIC {row["MOIC"]}x', sz=13, c=D_GREEN, bold=True)
            _text(s, Inches(5.5), y+Inches(0.03), Inches(1.5), Inches(0.25), f'IRR {row["IRR(%)"]}%', sz=11, c=D_GREY)
        _text(s, Inches(7.0), Inches(1.5), Inches(5), Inches(0.3), "UNDERPERFORMERS", sz=11, c=RED_SOFT, bold=True)
        for i, (_, row) in enumerate(sd.tail(3).iterrows()):
            y = Inches(1.9) + Inches(i * 0.7)
            clr = RED_SOFT if row["MOIC"] < 1.0 else GREY
            _circle_num(s, Inches(7.0), y, str(i+1), bg=clr)
            _text(s, Inches(7.6), y+Inches(0.03), Inches(2.5), Inches(0.25), row["회사명"], sz=14, c=BLACK, bold=True)
            _text(s, Inches(10.2), y+Inches(0.03), Inches(1.5), Inches(0.25), f'MOIC {row["MOIC"]}x', sz=13, c=clr, bold=True)
            _text(s, Inches(11.7), y+Inches(0.03), Inches(1.5), Inches(0.25), f'IRR {row["IRR(%)"]}%', sz=11, c=D_GREY)

        if include_charts:
            import plotly.graph_objects as go
            tb = pd.concat([sd.head(3), sd.tail(3)]).sort_values("MOIC", ascending=True)
            cs = ["#1b5e20" if m >= 2 else "#43a047" if m >= 1 else "#e0a0a0" for m in tb["MOIC"]]
            fig = go.Figure(go.Bar(x=tb["MOIC"].tolist(), y=tb["회사명"].tolist(), orientation="h", marker_color=cs,
                text=[f"{m}x" for m in tb["MOIC"]], textposition="outside"))
            fig.update_layout(height=180, width=450, margin=dict(t=5,b=5,l=80,r=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor="#eee"), yaxis=dict(showgrid=False), bargap=0.3)
            _add_chart_to_slide(s, fig, 0.8, 4.8, 5.0, 2.2)
        slides.append("Top/Bottom")

    # ═══ 6. 집중도 ═══
    if _sec("집중도"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "PORTFOLIO ANALYTICS", "포트폴리오 집중도 · 투자 경과")
        weights = result_df["투자금액_백만원"] / result_df["투자금액_백만원"].sum()
        hhi = round((weights ** 2).sum() * 10000)
        hhi_label = "High" if hhi > 2500 else ("Medium" if hhi > 1500 else "Low (Diversified)")
        _metric_card(s, Inches(0.8), Inches(1.5), Inches(3.5), Inches(1.5), "HHI INDEX", f"{hhi:,}", hhi_label, val_color=RED_SOFT if hhi > 2500 else D_GREEN)
        import datetime
        avg_days = (pd.to_datetime(result_df.iloc[0].get("기준일", datetime.date.today())) - pd.to_datetime(result_df["투자일"].min())).days if "투자일" in result_df.columns else 0
        avg_years = round(avg_days / 365.25, 1) if avg_days > 0 else 0
        total_val = result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum()
        realized_pct = round(result_df["회수금액_백만원"].sum() / total_val * 100, 1) if total_val > 0 else 0
        _metric_card(s, Inches(4.8), Inches(1.5), Inches(3.5), Inches(1.5), "AVG HOLDING", f"{avg_years}yr", "평균 보유 기간")
        _metric_card(s, Inches(8.8), Inches(1.5), Inches(3.5), Inches(1.5), "REALIZATION", f"{realized_pct}%", "현금 실현율", val_color=D_GREEN if realized_pct > 50 else BLACK)
        if "투자단계" in result_df.columns:
            _text(s, Inches(0.8), Inches(3.5), Inches(5), Inches(0.3), "INVESTMENT STAGE MIX", sz=11, c=GREY, bold=True)
            for i, (stage, cnt) in enumerate(result_df["투자단계"].value_counts().items()):
                x = Inches(0.8) + Inches(i * 2.5)
                if x > Inches(11): break
                pct = cnt / len(result_df)
                _rounded(s, x, Inches(3.9), Inches(2.2), Inches(0.8), XP_GREEN, P_GREEN)
                _text(s, x, Inches(3.95), Inches(2.2), Inches(0.25), stage, sz=11, c=D_GREEN, bold=True, align=PP_ALIGN.CENTER)
                _text(s, x, Inches(4.25), Inches(2.2), Inches(0.25), f"{cnt}개사 ({pct*100:.0f}%)", sz=10, c=D_GREY, align=PP_ALIGN.CENTER)
        slides.append("집중도")

    # ═══ 7. 리스크 ═══
    if _sec("리스크"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "RISK ASSESSMENT", "리스크 평가")
        weights_r = result_df["투자금액_백만원"] / result_df["투자금액_백만원"].sum()
        hhi_r = round((weights_r ** 2).sum() * 10000)
        risks = []
        under = result_df[result_df["MOIC"] < 1.0]
        if len(under) > 0: risks.append(("MOIC 1.0x 미만", f"{len(under)}개사: {', '.join(under['회사명'].tolist())}", "HIGH", "!"))
        if hhi_r > 2500: risks.append(("집중 리스크", f"HHI {hhi_r:,} — 특정 기업에 투자 편중", "HIGH", "!"))
        elif hhi_r > 1500: risks.append(("집중도 보통", f"HHI {hhi_r:,} — 분산 확대 검토", "MEDIUM", "△"))
        if summary["펀드 DPI"] < 0.5: risks.append(("회수 지연", f"DPI {summary['펀드 DPI']}x — 실현 수익 제한적", "MEDIUM", "△"))
        if summary["펀드 MOIC"] >= 2.0: risks.append(("우수 성과", f"MOIC {summary['펀드 MOIC']}x — 벤치마크 달성", "POSITIVE", "✓"))
        if avg_irr > 15: risks.append(("IRR 달성", f"IRR {avg_irr}% — 목표 15% 초과", "POSITIVE", "✓"))

        # 좌측: 리스크 요약 게이지
        high_cnt = sum(1 for r in risks if r[2] == "HIGH")
        med_cnt = sum(1 for r in risks if r[2] == "MEDIUM")
        pos_cnt = sum(1 for r in risks if r[2] == "POSITIVE")

        _rounded(s, Inches(0.8), Inches(1.5), Inches(3.0), Inches(1.2), WHITE, BORDER)
        _text(s, Inches(0.8), Inches(1.55), Inches(3.0), Inches(0.2), "RISK OVERVIEW", sz=9, c=GREY, bold=True, align=PP_ALIGN.CENTER)
        gauge_items = []
        if high_cnt > 0: gauge_items.append((f"HIGH  {high_cnt}", RED_SOFT))
        if med_cnt > 0: gauge_items.append((f"MEDIUM  {med_cnt}", RGBColor(0xFF,0x98,0x00)))
        if pos_cnt > 0: gauge_items.append((f"POSITIVE  {pos_cnt}", D_GREEN))
        for j, (label, clr) in enumerate(gauge_items):
            gx = Inches(0.95) + Inches(j * 1.0)
            _circle(s, gx, Inches(2.0), Inches(0.35), clr)
            _text(s, gx, Inches(2.0), Inches(0.35), Inches(0.35), str(high_cnt if "HIGH" in label else med_cnt if "MEDIUM" in label else pos_cnt),
                  sz=12, c=WHITE, bold=True, align=PP_ALIGN.CENTER)
            _text(s, gx - Inches(0.1), Inches(2.4), Inches(0.55), Inches(0.2),
                  label.split()[0], sz=7, c=clr, bold=True, align=PP_ALIGN.CENTER)

        # 우측: 상세 카드
        for i, (title, desc, level, icon) in enumerate(risks):
            y = Inches(1.5) + Inches(i * 0.75)
            if level == "HIGH": clr, bg_c, border_c = RED_SOFT, RGBColor(0xFE,0xF5,0xF5), RGBColor(0xF0,0xD0,0xD0)
            elif level == "MEDIUM": clr, bg_c, border_c = RGBColor(0xFF,0x98,0x00), RGBColor(0xFF,0xF8,0xEE), RGBColor(0xF0,0xE0,0xC0)
            else: clr, bg_c, border_c = D_GREEN, RGBColor(0xF2,0xF9,0xF2), RGBColor(0xC8,0xE6,0xC9)

            _rounded(s, Inches(4.2), y, Inches(8.3), Inches(0.6), bg_c, border_c)
            _circle(s, Inches(4.35), y + Inches(0.1), Inches(0.4), clr)
            _text(s, Inches(4.35), y + Inches(0.1), Inches(0.4), Inches(0.4), icon, sz=14, c=WHITE, bold=True, align=PP_ALIGN.CENTER)
            _text(s, Inches(4.95), y + Inches(0.08), Inches(2.5), Inches(0.2), title, sz=12, c=BLACK, bold=True)
            _text(s, Inches(4.95), y + Inches(0.32), Inches(7.3), Inches(0.2), desc, sz=9, c=D_GREY)
        slides.append("리스크")

    # ═══ J-Curve ═══
    if _sec("J-Curve") and jcurve_df is not None and not jcurve_df.empty:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "J-CURVE ANALYSIS", "J-Curve 현금흐름")
        mn = jcurve_df["누적현금흐름"].min()
        cr = jcurve_df["누적현금흐름"].iloc[-1]
        be = jcurve_df[jcurve_df["누적현금흐름"] >= 0]
        be_dt = str(be["날짜"].iloc[0])[:10] if not be.empty else "미도달"
        _metric_card(s, Inches(0.8), Inches(1.5), Inches(3.5), Inches(1.3), "MAX DRAWDOWN", f"{mn:,.0f}M", "최대 누적 손실", val_color=RED_SOFT)
        _metric_card(s, Inches(4.8), Inches(1.5), Inches(3.5), Inches(1.3), "CURRENT CF", f"{cr:,.0f}M", "현재 누적 현금흐름", val_color=D_GREEN if cr >= 0 else RED_SOFT)
        _metric_card(s, Inches(8.8), Inches(1.5), Inches(3.5), Inches(1.3), "BREAK-EVEN", be_dt, "손익분기 시점")
        if include_charts:
            import plotly.graph_objects as go
            dates = jcurve_df["날짜"].astype(str).tolist()
            cf = jcurve_df["누적현금흐름"].tolist()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=cf, mode="lines+markers",
                line=dict(color="#1b5e20", width=2.5), fill="tozeroy", fillcolor="rgba(27,94,32,0.08)",
                marker=dict(size=5, color=["#1b5e20" if v >= 0 else "#e0a0a0" for v in cf])))
            fig.add_hline(y=0, line_dash="dash", line_color="#ccc")
            fig.update_layout(height=280, width=700, margin=dict(t=5,b=25,l=50,r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="백만원"))
            _add_chart_to_slide(s, fig, 0.8, 3.2, 7.0, 3.5)
        slides.append("J-Curve")

    # ═══ 시나리오 ═══
    if _sec("시나리오") and scenario_df is not None and not scenario_df.empty:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "EXIT SCENARIO", f"회수 시나리오 — {scenario_company}")
        if include_charts and "Exit 배수" in scenario_df.columns and "IRR (%)" in scenario_df.columns:
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(
                x=scenario_df["Exit 배수"].tolist(), y=scenario_df["IRR (%)"].tolist(),
                marker_color=["#1b5e20" if v >= 20 else "#43a047" if v >= 0 else "#e0a0a0" for v in scenario_df["IRR (%)"]],
                text=[f"{v}%" for v in scenario_df["IRR (%)"]], textposition="outside",
                marker_line_width=0,
            ))
            fig.update_layout(height=320, width=700, margin=dict(t=10,b=30,l=40,r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False, bargap=0.3,
                xaxis=dict(showgrid=False, title="Exit 배수"), yaxis=dict(showgrid=True, gridcolor="#eee", title="IRR (%)"))
            _add_chart_to_slide(s, fig, 0.8, 1.5, 7.0, 4.0)
        else:
            cols = list(scenario_df.columns)
            for i, (_, row) in enumerate(scenario_df.iterrows()):
                y = Inches(1.5) + Inches(i * 0.5)
                _text(s, Inches(0.8), y, Inches(3), Inches(0.25), f'Exit {row.get("Exit 배수","")}x', sz=12, c=BLACK, bold=True)
                _text(s, Inches(4.0), y, Inches(3), Inches(0.25), f'IRR {row.get("IRR (%)","")}%', sz=12, c=D_GREEN)
        slides.append("시나리오")

    # ═══ 8. Waterfall ═══
    if _sec("Waterfall"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "WATERFALL DISTRIBUTION", "Waterfall 분배 시뮬레이션")
        wf_inv = float(total_inv); wf_proc = float(result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum())
        hurdle, carry, years = 8, 20, 5
        profit = max(0, wf_proc - wf_inv); hurdle_amt = wf_inv * ((1+hurdle/100)**years - 1)
        rem = wf_proc; s1 = min(rem, wf_inv); rem -= s1; s2 = min(rem, hurdle_amt); rem -= s2
        gp_t = profit * carry / 100; s3_gp = min(rem, gp_t); rem -= s3_gp
        s4_gp = rem * carry / 100; s4_lp = rem - s4_gp
        total_lp = s1 + s2 + s4_lp; total_gp = s3_gp + s4_gp
        lp_moic = total_lp / wf_inv if wf_inv > 0 else 0

        if include_charts:
            import plotly.graph_objects as go
            labels = ["① 원금 반환", "② 우선수익", "③ GP Catch-up", "④ Carry Split"]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="LP", x=labels, y=[s1, s2, 0, s4_lp], marker_color="#1b5e20", text=[f"{v:,.0f}" for v in [s1,s2,0,s4_lp]], textposition="inside", textfont=dict(color="#fff")))
            fig.add_trace(go.Bar(name="GP", x=labels, y=[0, 0, s3_gp, s4_gp], marker_color="#a5d6a7", text=[f"{v:,.0f}" if v > 0 else "" for v in [0,0,s3_gp,s4_gp]], textposition="inside"))
            fig.update_layout(barmode="stack", height=280, width=600, margin=dict(t=10,b=30,l=40,r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=-0.15), bargap=0.3, yaxis=dict(showgrid=True, gridcolor="#eee"))
            _add_chart_to_slide(s, fig, 0.8, 1.5, 6.5, 3.0)
        else:
            param_txt = f"투자금 {wf_inv:,.0f}M · 회수금 {wf_proc:,.0f}M · Hurdle {hurdle}% · Carry {carry}% · {years}년"
            _rounded(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.5), XP_GREEN, P_GREEN)
            _text(s, Inches(1.0), Inches(1.55), Inches(11.3), Inches(0.35), param_txt, sz=11, c=D_GREEN, bold=True, align=PP_ALIGN.CENTER)
            max_val = max(wf_proc * 0.6, 1)
            for i, (nm, lp, gp, clr, desc) in enumerate([("① 원금 반환",s1,0,D_GREEN,"LP 원금"), ("② 우선수익",s2,0,M_GREEN,f"Hurdle {hurdle}%"), ("③ GP 캐치업",0,s3_gp,GREEN,"GP Carry"), ("④ 초과수익",s4_lp,s4_gp,L_GREEN,f"LP/GP Split")]):
                y = Inches(2.3) + Inches(i * 0.85)
                _text(s, Inches(0.8), y, Inches(2.0), Inches(0.25), nm, sz=12, c=BLACK, bold=True)
                _bar_visual(s, Inches(3.0), y+Inches(0.04), Inches(5.5), Inches(0.22), max(lp/max_val, 0.01), D_GREEN, P_GREEN)
                _text(s, Inches(8.8), y, Inches(1.5), Inches(0.25), f"LP {lp:,.0f}", sz=9, c=D_GREEN, bold=True)
                _text(s, Inches(10.2), y, Inches(1.5), Inches(0.25), f"GP {gp:,.0f}" if gp > 0 else "", sz=9, c=GREEN)

        eff_carry = total_gp / profit * 100 if profit > 0 else 0
        for i, (lab, val) in enumerate([("LP 수취", f"{total_lp:,.0f}M"), ("GP Carry", f"{total_gp:,.0f}M"), ("LP MOIC", f"{lp_moic:.2f}x"), ("실효 Carry", f"{eff_carry:.1f}%")]):
            x = Inches(0.8) + Inches(i * 3.05)
            _text(s, x, Inches(5.8), Inches(1.5), Inches(0.2), lab, sz=9, c=GREY)
            _text(s, x+Inches(1.5), Inches(5.8), Inches(1.5), Inches(0.2), val, sz=11, c=D_GREEN, bold=True)
        slides.append("Waterfall")

    # ═══ 9. AI 코멘터리 ═══
    if _sec("AI") and commentary:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "AI COMMENTARY", "분기 코멘터리 — Claude AI")
        _rounded(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3), WHITE, P_GREEN)
        _circle(s, Inches(1.1), Inches(1.7), Inches(0.4), D_GREEN)
        _text(s, Inches(1.1), Inches(1.7), Inches(0.4), Inches(0.4), "AI", sz=9, c=WHITE, bold=True, align=PP_ALIGN.CENTER)
        _text(s, Inches(1.65), Inches(1.75), Inches(4), Inches(0.3), "Claude AI 자동 생성 코멘터리", sz=12, c=D_GREEN, bold=True)
        lines = [l for l in commentary.split("\n") if l.strip()][:18]
        _multi(s, Inches(1.1), Inches(2.3), Inches(11.0), Inches(4.2), lines, sz=11, c=D_GREY, spacing=5)
        slides.append("AI")

    # ═══ Thank You (항상) ═══
    total_slides = len(slides) + 1
    s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s, D_GREEN)
    _circle(s, Inches(9), Inches(-1.5), Inches(6), M_GREEN)
    _circle(s, Inches(10), Inches(-0.5), Inches(4), GREEN)
    _circle(s, Inches(-1.5), Inches(5), Inches(4), M_GREEN)
    _rect(s, Inches(0), Inches(0), W, Inches(0.05), L_GREEN)
    _rect(s, Inches(0), Inches(7.45), W, Inches(0.05), L_GREEN)
    _text(s, Inches(1.5), Inches(2.2), Inches(10), Inches(0.8), "Thank You", sz=56, c=WHITE, bold=True)
    _rect(s, Inches(1.5), Inches(3.3), Inches(2), Pt(2), L_GREEN)
    _text(s, Inches(1.5), Inches(3.6), Inches(10), Inches(0.4), f"{fund_name}  ·  {quarter}", sz=15, c=L_GREEN)
    _text(s, Inches(1.5), Inches(4.2), Inches(10), Inches(0.3), "PE/VC 분기 보고 도우미  ·  SDIC  ·  이수빈", sz=12, c=P_GREEN)
    _text(s, Inches(1.5), Inches(5.5), Inches(10), Inches(0.3), "본 보고서는 자동 생성된 참고 자료입니다.", sz=9, c=L_GREEN)

    # 페이지 번호 추가
    total_slides = len(prs.slides)
    for i, slide in enumerate(prs.slides):
        if i > 0 and i < total_slides - 1:
            _page(slide, i + 1, total_slides)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
