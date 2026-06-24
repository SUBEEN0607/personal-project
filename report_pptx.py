"""
LP 보고서 PPTX 생성 모듈 — 앱 내 다운로드용
포트폴리오 상세 · 섹터 분석 · Waterfall · AI 코멘터리 포함
"""
import io
import os
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
WARM     = RGBColor(0xF5, 0xF3, 0xEF)
RED_SOFT = RGBColor(0xC6, 0x28, 0x28)

FONT = "맑은 고딕"
W = Inches(13.333)
H = Inches(7.5)


# ── 헬퍼 ──

def _bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def _rect(s, l, t, w, h, c, border=None):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    r.fill.solid()
    r.fill.fore_color.rgb = c
    if border:
        r.line.color.rgb = border
        r.line.width = Pt(1)
    else:
        r.line.fill.background()
    return r

def _rounded(s, l, t, w, h, c=WHITE, border=BORDER):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    r.fill.solid()
    r.fill.fore_color.rgb = c
    r.line.color.rgb = border
    r.line.width = Pt(1)
    r.adjustments[0] = 0.04
    return r

def _circle(s, l, t, size, c=D_GREEN):
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, l, t, size, size)
    o.fill.solid()
    o.fill.fore_color.rgb = c
    o.line.fill.background()

def _text(s, l, t, w, h, txt, sz=14, c=BLACK, bold=False, align=PP_ALIGN.LEFT):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(txt)
    p.font.size = Pt(sz)
    p.font.color.rgb = c
    p.font.bold = bold
    p.font.name = FONT
    p.alignment = align
    p.space_after = Pt(0)
    return tb

def _multi(s, l, t, w, h, lines, sz=12, c=BLACK, spacing=6):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = str(line)
        p.font.size = Pt(sz)
        p.font.color.rgb = c
        p.font.name = FONT
        p.space_after = Pt(spacing)
    return tb

def _circle_num(s, l, t, txt, bg=D_GREEN, fg=WHITE):
    _circle(s, l, t, Inches(0.4), bg)
    _text(s, l, t, Inches(0.4), Inches(0.4), txt, sz=11, c=fg, bold=True, align=PP_ALIGN.CENTER)

def _header(s, label, title):
    _text(s, Inches(0.8), Inches(0.35), Inches(6), Inches(0.2),
          label, sz=9, c=GREY, bold=True)
    _text(s, Inches(0.8), Inches(0.6), Inches(11), Inches(0.5),
          title, sz=26, c=BLACK, bold=True)
    _rect(s, Inches(0.8), Inches(1.15), Inches(0.6), Pt(3), D_GREEN)
    _rect(s, Inches(1.5), Inches(1.15), Inches(11), Pt(1), BORDER)

def _page(s, n, total):
    _text(s, Inches(12.0), Inches(7.05), Inches(1.2), Inches(0.3),
          f"{n}/{total}", sz=8, c=L_GREY, align=PP_ALIGN.RIGHT)

def _metric_card(s, l, t, w, h, label, value, sub="", bg=WHITE, val_color=D_GREEN):
    _rounded(s, l, t, w, h, bg, BORDER)
    _text(s, l, t + Inches(0.15), w, Inches(0.2),
          label, sz=9, c=GREY, bold=True, align=PP_ALIGN.CENTER)
    _text(s, l, t + Inches(0.45), w, Inches(0.5),
          value, sz=30, c=val_color, bold=True, align=PP_ALIGN.CENTER)
    if sub:
        _text(s, l, t + Inches(1.0), w, Inches(0.2),
              sub, sz=8, c=GREY, align=PP_ALIGN.CENTER)

def _bar_visual(s, l, t, w, h, pct, color=D_GREEN, bg=P_GREEN):
    """수평 프로그레스 바"""
    _rounded(s, l, t, w, h, bg, bg)
    fill_w = max(int(w * min(pct, 1.0)), Inches(0.05))
    _rect(s, l, t, fill_w, h, color)


# ══════════════════════════════════════════════════
def generate_lp_pptx(
    summary: dict,
    result_df: pd.DataFrame,
    commentary: str,
    quarter: str = "",
    fund_name: str = "PE/VC 펀드",
    fund_strategy: str = "VC",
    base_date: str = "",
) -> bytes:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    TOTAL = 10

    moic = summary["펀드 MOIC"]
    dpi = summary["펀드 DPI"]
    rvpi = summary["펀드 RVPI"]
    tvpi = summary["펀드 TVPI"]
    avg_irr = round(result_df["IRR(%)"].mean(), 1)
    n = summary["포트폴리오사 수"]
    total_inv = summary["총 투자금액 (백만원)"]

    # ═══════════════════════════════════════════════
    # 1. 표지
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, D_GREEN)

    # 배경 이미지
    _img_path = ""
    for _p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "skku_wallpaper.jpg"),
        os.path.join(os.getcwd(), "skku_wallpaper.jpg"),
        r"C:\Users\Lenovo\personal-project\skku_wallpaper.jpg",
    ]:
        if os.path.exists(_p):
            _img_path = _p
            break
    if _img_path:
        s.shapes.add_picture(_img_path, Inches(0), Inches(0), W, H)

    # 반투명 오버레이 (이미지 위에 어두운 초록 막)
    overlay = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), W, H)
    overlay.fill.solid()
    overlay.fill.fore_color.rgb = RGBColor(0x10, 0x30, 0x12)
    overlay.line.fill.background()
    try:
        from pptx.oxml.ns import nsmap
        a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
        fill_elem = overlay._element.find(f'.//{{{a_ns}}}solidFill')
        if fill_elem is not None:
            from lxml import etree
            clr_elem = fill_elem[0]
            alpha_elem = etree.SubElement(clr_elem, f'{{{a_ns}}}alpha')
            alpha_elem.set('val', '45000')
    except Exception:
        pass

    _text(s, Inches(1.2), Inches(1.3), Inches(8), Inches(0.2),
          "QUARTERLY PORTFOLIO REPORT", sz=10, c=L_GREEN, bold=True)
    _rect(s, Inches(1.2), Inches(1.7), Inches(0.8), Pt(3), L_GREEN)

    _text(s, Inches(1.2), Inches(2.0), Inches(8), Inches(0.8),
          fund_name, sz=44, c=WHITE, bold=True)
    _text(s, Inches(1.2), Inches(3.2), Inches(8), Inches(0.4),
          f"{fund_strategy}  ·  {quarter}  ·  {base_date}", sz=16, c=P_GREEN)

    # 표지 하단 요약 숫자
    stats = [
        ("MOIC", f"{moic}x"), ("IRR", f"{avg_irr}%"),
        ("TVPI", f"{tvpi}x"), ("Portfolio", f"{n}개사"),
    ]
    for i, (lab, val) in enumerate(stats):
        x = Inches(1.2) + Inches(i * 2.2)
        _text(s, x, Inches(5.0), Inches(2), Inches(0.2),
              lab, sz=9, c=L_GREEN)
        _text(s, x, Inches(5.3), Inches(2), Inches(0.4),
              val, sz=22, c=WHITE, bold=True)

    _text(s, Inches(1.2), Inches(6.3), Inches(8), Inches(0.2),
          "PE/VC 분기 보고 도우미  ·  SDIC", sz=10, c=L_GREEN)

    # ═══════════════════════════════════════════════
    # 2. 성과 요약 (Hero Metrics)
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "PERFORMANCE SUMMARY", "성과 요약")

    # Hero: MOIC + IRR
    _metric_card(s, Inches(0.8), Inches(1.5), Inches(5.7), Inches(1.5),
                 "MOIC", f"{moic}x", "투자원금 대비 전체 가치 배수")
    _metric_card(s, Inches(6.8), Inches(1.5), Inches(5.7), Inches(1.5),
                 "IRR", f"{avg_irr}%", "시간가치 반영 연환산 수익률")

    # 보조: DPI, RVPI, TVPI, 기업수
    sub_metrics = [
        ("DPI", f"{dpi}x", "현금 회수 배수"),
        ("RVPI", f"{rvpi}x", "잔존 가치"),
        ("TVPI", f"{tvpi}x", "DPI + RVPI"),
        ("투자기업", f"{n}개", f"총 {total_inv:,}M 투자"),
    ]
    for i, (lab, val, sub) in enumerate(sub_metrics):
        x = Inches(0.8) + Inches(i * 3.05)
        _metric_card(s, x, Inches(3.4), Inches(2.8), Inches(1.3),
                     lab, val, sub, bg=XP_GREEN, val_color=D_GREEN)

    # 벤치마크 비교 바
    _text(s, Inches(0.8), Inches(5.1), Inches(4), Inches(0.25),
          "벤치마크 비교", sz=12, c=BLACK, bold=True)

    benchmarks = [
        ("MOIC", moic, 2.0, "목표 ≥ 2.0x"),
        ("IRR", avg_irr, 15.0, "목표 ≥ 15%"),
        ("TVPI", tvpi, 2.0, "목표 ≥ 2.0x"),
    ]
    for i, (name, actual, target, desc) in enumerate(benchmarks):
        y = Inches(5.5) + Inches(i * 0.55)
        _text(s, Inches(0.8), y, Inches(1.0), Inches(0.2),
              name, sz=10, c=BLACK, bold=True)
        pct = min(float(actual) / float(target), 1.5) / 1.5
        _bar_visual(s, Inches(2.0), y + Inches(0.02), Inches(7.5), Inches(0.2), pct)
        color = D_GREEN if float(actual) >= target else RED_SOFT
        _text(s, Inches(9.8), y, Inches(1.5), Inches(0.2),
              f"{actual} / {target}", sz=9, c=color, bold=True)
        _text(s, Inches(11.3), y, Inches(1.5), Inches(0.2),
              desc, sz=8, c=GREY)

    _page(s, 2, TOTAL)

    # ═══════════════════════════════════════════════
    # 3. 포트폴리오 상세 (회사별 시각화)
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "PORTFOLIO DETAIL", "포트폴리오 상세")

    # 회사별 카드 (최대 8개)
    sorted_df = result_df.sort_values("MOIC", ascending=False).head(8)
    colors = [D_GREEN, M_GREEN, GREEN, L_GREEN, D_GREEN, M_GREEN, GREEN, L_GREEN]

    for i, (_, row) in enumerate(sorted_df.iterrows()):
        col = i % 4
        r = i // 4
        x = Inches(0.5) + Inches(col * 3.15)
        y = Inches(1.5) + Inches(r * 2.8)
        clr = colors[i % len(colors)]

        _rounded(s, x, y, Inches(2.9), Inches(2.5), WHITE, BORDER)

        # 번호 원
        _circle_num(s, x + Inches(0.15), y + Inches(0.15), str(i + 1), bg=clr)

        # 회사명 + 섹터
        _text(s, x + Inches(0.65), y + Inches(0.18), Inches(2.0), Inches(0.25),
              row["회사명"], sz=13, c=BLACK, bold=True)
        _text(s, x + Inches(0.65), y + Inches(0.45), Inches(2.0), Inches(0.2),
              f'{row["섹터"]} · {row["투자단계"]}', sz=8, c=GREY)

        # MOIC 바
        moic_val = float(row["MOIC"])
        moic_pct = min(moic_val / 5.0, 1.0)
        _text(s, x + Inches(0.15), y + Inches(0.85), Inches(0.8), Inches(0.2),
              "MOIC", sz=8, c=GREY, bold=True)
        _text(s, x + Inches(1.8), y + Inches(0.85), Inches(0.9), Inches(0.2),
              f"{moic_val}x", sz=10, c=clr, bold=True, align=PP_ALIGN.RIGHT)
        _bar_visual(s, x + Inches(0.15), y + Inches(1.1), Inches(2.55), Inches(0.15), moic_pct, clr)

        # IRR 바
        irr_val = float(row["IRR(%)"])
        irr_pct = min(max(irr_val, 0) / 50.0, 1.0)
        _text(s, x + Inches(0.15), y + Inches(1.4), Inches(0.8), Inches(0.2),
              "IRR", sz=8, c=GREY, bold=True)
        _text(s, x + Inches(1.8), y + Inches(1.4), Inches(0.9), Inches(0.2),
              f"{irr_val}%", sz=10, c=clr, bold=True, align=PP_ALIGN.RIGHT)
        _bar_visual(s, x + Inches(0.15), y + Inches(1.65), Inches(2.55), Inches(0.15), irr_pct, clr)

        # 하단: 투자금액 + TVPI
        _text(s, x + Inches(0.15), y + Inches(2.0), Inches(1.3), Inches(0.2),
              f'투자 {int(row["투자금액_백만원"]):,}M', sz=8, c=D_GREY)
        _text(s, x + Inches(1.5), y + Inches(2.0), Inches(1.2), Inches(0.2),
              f'TVPI {row["TVPI"]}x', sz=8, c=D_GREY, align=PP_ALIGN.RIGHT)

    _page(s, 3, TOTAL)

    # ═══════════════════════════════════════════════
    # 4. 섹터 분석
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "SECTOR ANALYSIS", "섹터별 분석")

    # 섹터별 집계
    if "섹터" in result_df.columns and "투자금액_백만원" in result_df.columns:
        sector_agg = result_df.groupby("섹터").agg(
            기업수=("회사명", "count"),
            총투자=("투자금액_백만원", "sum"),
            평균MOIC=("MOIC", "mean"),
            평균IRR=("IRR(%)", "mean"),
        ).sort_values("총투자", ascending=False).reset_index()

        total_all = sector_agg["총투자"].sum()
        num_sectors = min(len(sector_agg), 8)
        row_h = min(0.65, 5.0 / max(num_sectors, 1))

        for i, (_, row) in enumerate(sector_agg.head(8).iterrows()):
            y = Inches(1.5) + Inches(i * row_h)
            clr = colors[i % len(colors)]

            _circle_num(s, Inches(0.8), y, str(i + 1), bg=clr)
            _text(s, Inches(1.35), y + Inches(0.03), Inches(1.8), Inches(0.22),
                  row["섹터"], sz=12, c=BLACK, bold=True)

            pct = float(row["총투자"]) / total_all if total_all > 0 else 0
            _bar_visual(s, Inches(3.3), y + Inches(0.05), Inches(4.5), Inches(0.18), pct, clr)

            _text(s, Inches(8.0), y + Inches(0.03), Inches(0.8), Inches(0.22),
                  f"{pct*100:.0f}%", sz=11, c=clr, bold=True)
            _text(s, Inches(9.0), y + Inches(0.03), Inches(1.0), Inches(0.22),
                  f"{int(row['기업수'])}개사", sz=9, c=D_GREY)
            _text(s, Inches(10.1), y + Inches(0.03), Inches(1.2), Inches(0.22),
                  f"MOIC {row['평균MOIC']:.1f}x", sz=9, c=D_GREY)
            _text(s, Inches(11.3), y + Inches(0.03), Inches(1.2), Inches(0.22),
                  f"IRR {row['평균IRR']:.0f}%", sz=9, c=D_GREY)

        y_sum = Inches(1.5) + Inches(num_sectors * row_h) + Inches(0.15)
        _rect(s, Inches(0.8), y_sum, Inches(11.7), Pt(1), BORDER)
        _text(s, Inches(0.8), y_sum + Inches(0.1), Inches(6), Inches(0.22),
              f"전체 {len(sector_agg)}개 섹터 · {n}개사 · {total_inv:,}M 투자",
              sz=10, c=D_GREY, bold=True)

    _page(s, 4, TOTAL)

    # ═══════════════════════════════════════════════
    # 5. Top / Bottom Performers
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "TOP / BOTTOM PERFORMERS", "성과 상위 · 하위 분석")

    sorted_df = result_df.sort_values("MOIC", ascending=False)
    top3 = sorted_df.head(3)
    bottom3 = sorted_df.tail(3)

    _text(s, Inches(0.8), Inches(1.5), Inches(5), Inches(0.3),
          "TOP PERFORMERS", sz=11, c=D_GREEN, bold=True)
    for i, (_, row) in enumerate(top3.iterrows()):
        y = Inches(1.9) + Inches(i * 0.7)
        _circle_num(s, Inches(0.8), y, str(i+1), bg=D_GREEN)
        _text(s, Inches(1.4), y + Inches(0.03), Inches(2.5), Inches(0.25),
              row["회사명"], sz=14, c=BLACK, bold=True)
        _text(s, Inches(4.0), y + Inches(0.03), Inches(1.5), Inches(0.25),
              f'MOIC {row["MOIC"]}x', sz=13, c=D_GREEN, bold=True)
        _text(s, Inches(5.5), y + Inches(0.03), Inches(1.5), Inches(0.25),
              f'IRR {row["IRR(%)"]}%', sz=11, c=D_GREY)

    _text(s, Inches(7.0), Inches(1.5), Inches(5), Inches(0.3),
          "UNDERPERFORMERS", sz=11, c=RGBColor(0xC6,0x28,0x28), bold=True)
    for i, (_, row) in enumerate(bottom3.iterrows()):
        y = Inches(1.9) + Inches(i * 0.7)
        clr = RGBColor(0xC6,0x28,0x28) if row["MOIC"] < 1.0 else GREY
        _circle_num(s, Inches(7.0), y, str(i+1), bg=clr)
        _text(s, Inches(7.6), y + Inches(0.03), Inches(2.5), Inches(0.25),
              row["회사명"], sz=14, c=BLACK, bold=True)
        _text(s, Inches(10.2), y + Inches(0.03), Inches(1.5), Inches(0.25),
              f'MOIC {row["MOIC"]}x', sz=13, c=clr, bold=True)
        _text(s, Inches(11.7), y + Inches(0.03), Inches(1.5), Inches(0.25),
              f'IRR {row["IRR(%)"]}%', sz=11, c=D_GREY)

    _page(s, 5, TOTAL)

    # ═══════════════════════════════════════════════
    # 6. Portfolio Analytics (HHI + Timeline)
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "PORTFOLIO ANALYTICS", "포트폴리오 집중도 · 투자 경과")

    weights = result_df["투자금액_백만원"] / result_df["투자금액_백만원"].sum()
    hhi = round((weights ** 2).sum() * 10000)
    hhi_label = "High (Concentrated)" if hhi > 2500 else ("Medium" if hhi > 1500 else "Low (Diversified)")

    _metric_card(s, Inches(0.8), Inches(1.5), Inches(3.5), Inches(1.5),
                 "HHI INDEX", f"{hhi:,}", hhi_label,
                 val_color=RGBColor(0xC6,0x28,0x28) if hhi > 2500 else D_GREEN)

    import datetime
    avg_days = (pd.to_datetime(result_df.iloc[0].get("기준일", datetime.date.today())) -
                pd.to_datetime(result_df["투자일"].min())).days if "투자일" in result_df.columns else 0
    avg_years = round(avg_days / 365.25, 1) if avg_days > 0 else 0

    total_val = result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum()
    realized_pct = round(result_df["회수금액_백만원"].sum() / total_val * 100, 1) if total_val > 0 else 0

    _metric_card(s, Inches(4.8), Inches(1.5), Inches(3.5), Inches(1.5),
                 "AVG HOLDING", f"{avg_years}yr", "평균 투자 보유 기간")

    _metric_card(s, Inches(8.8), Inches(1.5), Inches(3.5), Inches(1.5),
                 "REALIZATION", f"{realized_pct}%", "현금 실현 비율",
                 val_color=D_GREEN if realized_pct > 50 else BLACK)

    # 투자 단계별 분포
    if "투자단계" in result_df.columns:
        _text(s, Inches(0.8), Inches(3.5), Inches(5), Inches(0.3),
              "INVESTMENT STAGE MIX", sz=11, c=GREY, bold=True)
        stage_counts = result_df["투자단계"].value_counts()
        for i, (stage, cnt) in enumerate(stage_counts.items()):
            x = Inches(0.8) + Inches(i * 2.5)
            if x > Inches(11): break
            pct = cnt / len(result_df)
            _rounded(s, x, Inches(3.9), Inches(2.2), Inches(0.8), XP_GREEN, P_GREEN)
            _text(s, x, Inches(3.95), Inches(2.2), Inches(0.25),
                  stage, sz=11, c=D_GREEN, bold=True, align=PP_ALIGN.CENTER)
            _text(s, x, Inches(4.25), Inches(2.2), Inches(0.25),
                  f"{cnt}개사 ({pct*100:.0f}%)", sz=10, c=D_GREY, align=PP_ALIGN.CENTER)

    _page(s, 6, TOTAL)

    # ═══════════════════════════════════════════════
    # 7. Risk Assessment
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "RISK ASSESSMENT", "리스크 평가")

    risks = []
    # MOIC < 1.0 기업
    underperformers = result_df[result_df["MOIC"] < 1.0]
    if len(underperformers) > 0:
        names = ", ".join(underperformers["회사명"].tolist())
        risks.append(("MOIC 1.0x 미만 기업", f"{len(underperformers)}개사: {names}", "HIGH"))
    # 집중도
    if hhi > 2500:
        risks.append(("포트폴리오 집중 리스크", f"HHI {hhi:,} — 특정 기업에 투자 편중", "HIGH"))
    elif hhi > 1500:
        risks.append(("포트폴리오 집중도 보통", f"HHI {hhi:,} — 분산 확대 검토 필요", "MEDIUM"))
    # DPI
    if summary["펀드 DPI"] < 0.5:
        risks.append(("현금 회수 지연", f"DPI {summary['펀드 DPI']}x — 실현 수익 제한적", "MEDIUM"))
    # 긍정 요소
    if summary["펀드 MOIC"] >= 2.0:
        risks.append(("우수한 전체 성과", f"MOIC {summary['펀드 MOIC']}x — 벤치마크 2.0x 달성", "POSITIVE"))
    if avg_irr > 15:
        risks.append(("목표 IRR 달성", f"IRR {avg_irr}% — 목표 15% 초과 달성", "POSITIVE"))

    for i, (title, desc, level) in enumerate(risks):
        y = Inches(1.5) + Inches(i * 0.9)
        if level == "HIGH":
            clr = RGBColor(0xC6,0x28,0x28)
            bg = RGBColor(0xFD,0xED,0xED)
        elif level == "MEDIUM":
            clr = RGBColor(0xFF,0x98,0x00)
            bg = RGBColor(0xFF,0xF3,0xE0)
        else:
            clr = D_GREEN
            bg = XP_GREEN
        _rounded(s, Inches(0.8), y, Inches(11.7), Inches(0.7), bg, clr)
        _text(s, Inches(1.0), y + Inches(0.08), Inches(0.8), Inches(0.22),
              level, sz=9, c=clr, bold=True)
        _text(s, Inches(2.0), y + Inches(0.08), Inches(3.0), Inches(0.22),
              title, sz=12, c=BLACK, bold=True)
        _text(s, Inches(5.2), y + Inches(0.08), Inches(7.0), Inches(0.22),
              desc, sz=10, c=D_GREY)

    _page(s, 7, TOTAL)

    # ═══════════════════════════════════════════════
    # 8. Waterfall 분배 시뮬레이션 (기본값)
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "WATERFALL DISTRIBUTION", "Waterfall 분배 시뮬레이션")

    # 기본 파라미터로 Waterfall 계산
    wf_invested = float(total_inv)
    wf_proceeds = float(result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum())
    wf_hurdle = 8
    wf_carry = 20
    wf_years = 5

    total_profit = max(0, wf_proceeds - wf_invested)

    # 파라미터 (1줄로 압축)
    param_txt = f"투자금 {wf_invested:,.0f}M  ·  회수금 {wf_proceeds:,.0f}M  ·  Hurdle {wf_hurdle}%  ·  Carry {wf_carry}%  ·  {wf_years}년"
    _rounded(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.5), XP_GREEN, P_GREEN)
    _text(s, Inches(1.0), Inches(1.55), Inches(11.3), Inches(0.35),
          param_txt, sz=11, c=D_GREEN, bold=True, align=PP_ALIGN.CENTER)

    # Waterfall 4단계 시각 바
    hurdle_amt = wf_invested * ((1 + wf_hurdle / 100) ** wf_years - 1)
    remaining = wf_proceeds

    step1 = min(remaining, wf_invested)
    remaining -= step1
    step2 = min(remaining, hurdle_amt)
    remaining -= step2
    gp_target = total_profit * wf_carry / 100
    step3_gp = min(remaining, gp_target)
    step3_lp = 0
    remaining -= step3_gp
    step4_gp = remaining * wf_carry / 100
    step4_lp = remaining - step4_gp

    total_lp = step1 + step2 + step3_lp + step4_lp
    total_gp = step3_gp + step4_gp
    lp_moic = total_lp / wf_invested if wf_invested > 0 else 0

    steps = [
        ("① 원금 반환", step1, 0, D_GREEN, "LP에게 투자원금 전액 반환"),
        ("② 우선수익", step2, 0, M_GREEN, f"Hurdle {wf_hurdle}% × {wf_years}년"),
        ("③ GP 캐치업", step3_lp, step3_gp, GREEN, f"GP Carry 목표 확보"),
        ("④ 초과수익", step4_lp, step4_gp, L_GREEN, f"LP {100-wf_carry}% / GP {wf_carry}%"),
    ]

    max_val = max(wf_proceeds * 0.6, 1)
    for i, (name, lp, gp, clr, desc) in enumerate(steps):
        y = Inches(2.3) + Inches(i * 0.85)

        _text(s, Inches(0.8), y, Inches(2.0), Inches(0.25),
              name, sz=12, c=BLACK, bold=True)

        # LP 바 (진한 초록)
        lp_w = max(lp / max_val, 0.01)
        _bar_visual(s, Inches(3.0), y + Inches(0.04), Inches(5.5), Inches(0.22),
                    lp_w, D_GREEN, P_GREEN)

        # GP 바 (연한 초록, LP 바 뒤에)
        if gp > 0:
            gp_w = max(gp / max_val, 0.01)
            gp_start = Inches(3.0) + int(Inches(5.5) * lp_w)
            _bar_visual(s, gp_start, y + Inches(0.04), Inches(5.5) - int(Inches(5.5) * lp_w), Inches(0.22),
                        gp_w, L_GREEN, P_GREEN)

        # 금액
        _text(s, Inches(8.8), y, Inches(1.5), Inches(0.25),
              f"LP {lp:,.0f}", sz=9, c=D_GREEN, bold=True)
        _text(s, Inches(10.2), y, Inches(1.5), Inches(0.25),
              f"GP {gp:,.0f}" if gp > 0 else "", sz=9, c=GREEN)
        _text(s, Inches(11.5), y, Inches(1.5), Inches(0.25),
              desc, sz=8, c=GREY)

    # 결과 요약
    y_res = Inches(5.8)
    _rect(s, Inches(0.8), y_res, Inches(11.7), Pt(1), BORDER)
    results = [
        ("LP 최종 수취", f"{total_lp:,.0f}M"),
        ("GP Carry 수취", f"{total_gp:,.0f}M"),
        ("LP MOIC", f"{lp_moic:.2f}x"),
        ("실효 Carry", f"{total_gp/total_profit*100:.1f}%" if total_profit > 0 else "0%"),
    ]
    for i, (lab, val) in enumerate(results):
        x = Inches(0.8) + Inches(i * 3.05)
        _text(s, x, y_res + Inches(0.2), Inches(1.5), Inches(0.2),
              lab, sz=9, c=GREY)
        _text(s, x + Inches(1.5), y_res + Inches(0.2), Inches(1.5), Inches(0.2),
              val, sz=11, c=D_GREEN, bold=True)

    _page(s, 8, TOTAL)

    # ═══════════════════════════════════════════════
    # 9. AI 코멘터리
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s)
    _header(s, "AI COMMENTARY", "분기 코멘터리 — Claude AI")

    _rounded(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.3), WHITE, P_GREEN)

    # 아이콘
    _circle(s, Inches(1.1), Inches(1.7), Inches(0.4), D_GREEN)
    _text(s, Inches(1.1), Inches(1.7), Inches(0.4), Inches(0.4),
          "AI", sz=9, c=WHITE, bold=True, align=PP_ALIGN.CENTER)
    _text(s, Inches(1.65), Inches(1.75), Inches(4), Inches(0.3),
          "Claude AI 자동 생성 코멘터리", sz=12, c=D_GREEN, bold=True)

    comment_lines = [l for l in commentary.split("\n") if l.strip()][:18]
    _multi(s, Inches(1.1), Inches(2.3), Inches(11.0), Inches(4.2),
           comment_lines, sz=11, c=D_GREY, spacing=5)

    _page(s, 9, TOTAL)

    # ═══════════════════════════════════════════════
    # 10. Thank You
    # ═══════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, D_GREEN)
    _circle(s, Inches(9), Inches(-1.5), Inches(6), M_GREEN)
    _circle(s, Inches(10), Inches(-0.5), Inches(4), GREEN)
    _circle(s, Inches(-1.5), Inches(5), Inches(4), M_GREEN)
    _rect(s, Inches(0), Inches(0), W, Inches(0.05), L_GREEN)
    _rect(s, Inches(0), Inches(7.45), W, Inches(0.05), L_GREEN)

    _text(s, Inches(1.5), Inches(2.2), Inches(10), Inches(0.8),
          "Thank You", sz=56, c=WHITE, bold=True)
    _rect(s, Inches(1.5), Inches(3.3), Inches(2), Pt(2), L_GREEN)
    _text(s, Inches(1.5), Inches(3.6), Inches(10), Inches(0.4),
          f"{fund_name}  ·  {quarter}", sz=15, c=L_GREEN)
    _text(s, Inches(1.5), Inches(4.2), Inches(10), Inches(0.3),
          "PE/VC 분기 보고 도우미  ·  SDIC  ·  이수빈", sz=12, c=P_GREEN)
    _text(s, Inches(1.5), Inches(5.5), Inches(10), Inches(0.3),
          "본 보고서는 자동 생성된 참고 자료입니다. 투자 결정의 근거로 단독 사용할 수 없습니다.",
          sz=9, c=L_GREEN)

    # ── 저장 ──
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
