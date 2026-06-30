"""
LP 보고서 PPTX — 컨설팅 장표 수준 재작성
모든 좌표를 픽셀 단위로 설계하여 겹침/공백 완전 제거
"""
import io, os, tempfile, datetime
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── 팔레트 ──────────────────────────────────────────
C_PRIMARY   = RGBColor(0x1B, 0x5E, 0x20)
C_SECONDARY = RGBColor(0x2E, 0x7D, 0x32)
C_ACCENT    = RGBColor(0x43, 0xA0, 0x47)
C_LIGHT     = RGBColor(0xA5, 0xD6, 0xA7)
C_PALE      = RGBColor(0xC8, 0xE6, 0xC9)
C_XPALE     = RGBColor(0xE8, 0xF5, 0xE9)
C_BG        = RGBColor(0xFA, 0xFA, 0xF8)
C_WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK     = RGBColor(0x1A, 0x1A, 0x1A)
C_DARK      = RGBColor(0x33, 0x33, 0x33)
C_GREY      = RGBColor(0x77, 0x77, 0x77)
C_LGREY     = RGBColor(0xBB, 0xBB, 0xBB)
C_BORDER    = RGBColor(0xE0, 0xE0, 0xE0)
C_RED       = RGBColor(0xC6, 0x28, 0x28)
C_ORANGE    = RGBColor(0xFF, 0x98, 0x00)
C_BEIGE     = RGBColor(0xF5, 0xF0, 0xE8)
C_INSIGHT   = RGBColor(0xF7, 0xF5, 0xF0)

FONT = "맑은 고딕"
SW, SH = Inches(13.333), Inches(7.5)

# 레이아웃 상수 — 모든 슬라이드 공통
M_LEFT   = Inches(0.6)          # 좌측 마진
M_RIGHT  = Inches(12.73)        # 우측 끝 (13.333-0.6)
C_WIDTH  = Inches(12.13)        # 콘텐츠 폭
TOP_BAR  = Inches(0.06)         # 상단 바 높이
HDR_Y    = Inches(0.25)         # 제목 Y
MSG_Y    = Inches(0.95)         # 핵심 메시지 Y
BODY_Y   = Inches(1.50)         # 본문 시작 Y (헤더+메시지 아래 충분한 간격)
BOT_Y    = Inches(7.10)         # 페이지 번호 Y

# ── 기본 헬퍼 ───────────────────────────────────────
def _bg(slide, color=C_BG):
    f = slide.background.fill; f.solid(); f.fore_color.rgb = color

def _shape(s, l, t, w, h, fill, border=None, radius=False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    r = s.shapes.add_shape(kind, l, t, w, h)
    r.fill.solid(); r.fill.fore_color.rgb = fill
    if border:
        r.line.color.rgb = border; r.line.width = Pt(0.75)
    else:
        r.line.fill.background()
    if radius:
        r.adjustments[0] = 0.03
    return r

def _txt(s, l, t, w, h, text, sz=10, color=C_BLACK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = str(text)
    p.font.size = Pt(sz); p.font.color.rgb = color; p.font.bold = bold
    p.font.name = font; p.alignment = align; p.space_after = Pt(0)
    tf.auto_size = None
    return tb

def _multiline(s, l, t, w, h, lines, sz=10, color=C_DARK, spacing=4, bold=False):
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = str(line)
        p.font.size = Pt(sz); p.font.color.rgb = color
        p.font.name = FONT; p.space_after = Pt(spacing); p.font.bold = bold
    return tb

# ── 컴포넌트 ───────────────────────────────────────
def _header(s, section_label, title, key_message=""):
    _shape(s, Inches(0), Inches(0), SW, TOP_BAR, C_PRIMARY)
    _txt(s, M_LEFT, HDR_Y, Inches(9), Inches(0.42), title,
         sz=24, color=C_BLACK, bold=True)
    _txt(s, Inches(10.0), HDR_Y + Inches(0.08), Inches(2.7), Inches(0.2),
         section_label, sz=8, color=C_GREY, align=PP_ALIGN.RIGHT)
    _shape(s, M_LEFT, Inches(0.72), C_WIDTH, Pt(2), C_PRIMARY)
    if key_message:
        _txt(s, M_LEFT, Inches(0.95), C_WIDTH, Inches(0.30),
             f"▸ {key_message}", sz=11, color=C_PRIMARY, bold=True)

def _page_num(s, n, total):
    _txt(s, Inches(12.0), BOT_Y, Inches(1.2), Inches(0.2),
         f"{n} / {total}", sz=7, color=C_LGREY, align=PP_ALIGN.RIGHT)

def _kpi_card(s, l, t, w, h, label, value, sub="", val_color=C_PRIMARY):
    _shape(s, l, t, w, h, C_WHITE, C_BORDER, radius=True)
    _txt(s, l, t + Inches(0.08), w, Inches(0.15), label,
         sz=8, color=C_GREY, bold=True, align=PP_ALIGN.CENTER)
    vy = t + Inches(0.28) if h >= Inches(1.0) else t + Inches(0.22)
    _txt(s, l, vy, w, Inches(0.35), str(value),
         sz=22 if h >= Inches(1.0) else 18, color=val_color, bold=True, align=PP_ALIGN.CENTER)
    if sub:
        _txt(s, l, t + h - Inches(0.22), w, Inches(0.18), sub,
             sz=7, color=C_GREY, align=PP_ALIGN.CENTER)

def _insight_panel(s, l, t, w, h, title, bullets):
    actual_h = max(h, Inches(0.40 + len(bullets[:6]) * 0.22))
    _shape(s, l, t, w, actual_h, C_INSIGHT, C_BORDER, radius=True)
    _txt(s, l + Inches(0.15), t + Inches(0.10), w - Inches(0.30), Inches(0.18),
         f"💡 {title}", sz=9, color=C_GREY, bold=True)
    for i, b in enumerate(bullets[:6]):
        _txt(s, l + Inches(0.15), t + Inches(0.35) + Inches(i * 0.22),
             w - Inches(0.30), Inches(0.20), f"· {b}", sz=9, color=C_DARK)

def _table(s, l, t, headers, rows, col_widths, row_h=Inches(0.32)):
    tbl = s.shapes.add_table(len(rows) + 1, len(headers), l, t,
                              sum(col_widths), row_h * (len(rows) + 1)).table
    for j, (hdr, cw) in enumerate(zip(headers, col_widths)):
        tbl.columns[j].width = cw
        cell = tbl.cell(0, j)
        cell.text = hdr
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(8); p.font.bold = True; p.font.color.rgb = C_WHITE
            p.font.name = FONT; p.alignment = PP_ALIGN.CENTER
        cell.fill.solid(); cell.fill.fore_color.rgb = C_PRIMARY
        cell.margin_top = Pt(4); cell.margin_bottom = Pt(4)
        cell.margin_left = Pt(4); cell.margin_right = Pt(4)
    for i, row_data in enumerate(rows):
        bg = C_WHITE
        for j, val in enumerate(row_data):
            cell = tbl.cell(i + 1, j)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(8); p.font.color.rgb = C_BLACK
                p.font.name = FONT; p.alignment = PP_ALIGN.CENTER
            cell.fill.solid(); cell.fill.fore_color.rgb = bg
            cell.margin_top = Pt(4); cell.margin_bottom = Pt(4)
            cell.margin_left = Pt(4); cell.margin_right = Pt(4)
    # 테이블 라인 스타일 — 얇은 회색 선
    try:
        from pptx.oxml.ns import qn
        tbl_elm = tbl._tbl
        tblPr = tbl_elm.find(qn('a:tblPr'))
        if tblPr is None:
            from lxml import etree
            tblPr = etree.SubElement(tbl_elm, qn('a:tblPr'))
        tblPr.set('bandRow', '0')
    except Exception:
        pass
    return tbl

def _bar_h(s, l, t, w, h, pct, fill=C_PRIMARY, bg=C_PALE):
    _shape(s, l, t, w, h, bg, radius=True)
    fw = max(int(w * min(pct, 1.0)), Inches(0.05))
    _shape(s, l, t, fw, h, fill, radius=True)

def _chart_img(s, fig, l, t, w_in, h_in):
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.write_image(tmp.name, width=int(w_in * 100), height=int(h_in * 100),
                        scale=2, engine="kaleido")
        s.shapes.add_picture(tmp.name, Inches(l), Inches(t), Inches(w_in))
        os.unlink(tmp.name)
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# 메인 생성 함수
# ══════════════════════════════════════════════════════
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
    sensitivity_df=None, sensitivity_company: str = "",
    dart_fin_df=None, dart_company: str = "",
    kvic_sector_df=None,
    rate_df=None, fx_df=None, spread=None,
    df_raw=None,
) -> bytes:

    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH

    sel = set(selected_sections) if selected_sections else set()
    include_all = len(sel) == 0
    def _sec(kw):
        return include_all or any(kw in s for s in sel)

    # 자주 쓰는 값
    moic     = summary["펀드 MOIC"]
    dpi      = summary["펀드 DPI"]
    rvpi     = summary["펀드 RVPI"]
    tvpi     = summary["펀드 TVPI"]
    avg_irr  = round(result_df["IRR(%)"].mean(), 1)
    n_cos    = summary["포트폴리오사 수"]
    total_inv = summary["총 투자금액 (백만원)"]
    total_val = result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum()

    slide_labels = []

    # ════════════════════════════════════════════════
    # 1. 표지 (항상 포함) — 상단 컬러블록 + 하단 흰색
    # ════════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, C_WHITE)

    # 상단 초록 블록 (슬라이드 약 75%)
    cover_h = Inches(5.5)
    _shape(s, Inches(0), Inches(0), SW, cover_h, C_PRIMARY)

    # 배경 이미지 (있으면 상단 블록 위에)
    for _p in [os.path.join(os.path.dirname(os.path.abspath(__file__)), "skku_wallpaper.jpg"),
               os.path.join(os.getcwd(), "skku_wallpaper.jpg")]:
        if os.path.exists(_p):
            s.shapes.add_picture(_p, Inches(0), Inches(0), SW, cover_h)
            # 반투명 오버레이
            ov = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), SW, cover_h)
            ov.fill.solid(); ov.fill.fore_color.rgb = RGBColor(0x10, 0x30, 0x12)
            ov.line.fill.background()
            try:
                ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
                fe = ov._element.find(f'.//{{{ns}}}solidFill')
                if fe is not None:
                    from lxml import etree
                    etree.SubElement(fe[0], f'{{{ns}}}alpha').set('val', '40000')
            except Exception:
                pass
            break

    # 제목 (상단 블록 중앙)
    _txt(s, Inches(1.2), Inches(1.8), Inches(10), Inches(0.8),
         fund_name, sz=42, color=C_WHITE, bold=True)
    _txt(s, Inches(1.2), Inches(2.8), Inches(10), Inches(0.5),
         f"{fund_strategy} 포트폴리오 {quarter} 분기 성과 보고서", sz=18, color=C_PALE)

    # 하단 흰색 영역 — 정보
    _shape(s, Inches(0), cover_h, SW, SH - cover_h, C_WHITE)
    _shape(s, Inches(0), cover_h, SW, Pt(4), C_PRIMARY)

    _txt(s, Inches(1.2), cover_h + Inches(0.25), Inches(5), Inches(0.22),
         f"{base_date}", sz=12, color=C_DARK)
    _txt(s, Inches(1.2), cover_h + Inches(0.55), Inches(5), Inches(0.22),
         "이수빈  ·  SDIC  ·  PE/VC 분기 보고 도우미", sz=10, color=C_GREY)
    _txt(s, Inches(1.2), cover_h + Inches(0.85), Inches(8), Inches(0.18),
         "본 보고서는 포트폴리오 성과 데이터를 기반으로 자동 생성되었습니다.", sz=8, color=C_LGREY)

    slide_labels.append("표지")

    # ════════════════════════════════════════════════
    # 2. Executive Summary
    # ════════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
    _header(s, "Executive Summary", "Executive Summary",
            f"{fund_name}의 {quarter} 포트폴리오 성과를 종합 요약합니다.")

    # 핵심 지표 한줄 요약
    total_cur = result_df["현재가치_백만원"].sum()
    total_rec = result_df["회수금액_백만원"].sum()
    total_profit = (total_cur + total_rec) - total_inv
    profit_pct = total_profit / total_inv * 100 if total_inv > 0 else 0

    _txt(s, M_LEFT, BODY_Y, C_WIDTH, Inches(0.30),
         f"{n_cos}개 기업에 총 {total_inv:,}백만원을 투자하여 MOIC {moic}x, IRR {avg_irr}%의 성과를 달성하였습니다.",
         sz=13, color=C_BLACK, bold=True)

    # 요약 테이블 — 예시 이미지처럼 좌측 라벨 + 우측 내용
    es_y = BODY_Y + Inches(0.55)
    es_items = [
        ("펀드 개요", f"{fund_name} · {fund_strategy} · {quarter} · 기준일 {base_date}"),
        ("포트폴리오", f"{n_cos}개 기업, 총 투자금 {total_inv:,}백만원"),
        ("핵심 성과", f"MOIC {moic}x · IRR {avg_irr}% · TVPI {tvpi}x · DPI {dpi}x · RVPI {rvpi}x"),
        ("가치 창출", f"투자 {total_inv:,.0f}M → 가치 {total_cur+total_rec:,.0f}M (수익률 {profit_pct:+.0f}%)"),
        ("벤치마크", f"MOIC {'달성' if moic >= 2.0 else '미달'}(목표 2.0x) · IRR {'달성' if avg_irr >= 15 else '미달'}(목표 15%)"),
    ]
    bm_over = len(result_df[result_df["MOIC"] >= 2.0])
    bm_under = len(result_df[result_df["MOIC"] < 1.0])
    es_items.append(("등급 분포", f"BM 달성 {bm_over}개사 · 원금 미달 {bm_under}개사 · 전체 {n_cos}개사"))

    # Top performer
    top_r = result_df.sort_values("MOIC", ascending=False).iloc[0]
    bot_r = result_df.sort_values("MOIC", ascending=True).iloc[0]
    es_items.append(("Top/Bottom", f"최고 {top_r['회사명']}({top_r['MOIC']}x) · 최저 {bot_r['회사명']}({bot_r['MOIC']}x)"))

    realized_ratio = total_rec / (total_cur + total_rec) * 100 if (total_cur + total_rec) > 0 else 0
    es_items.append(("회수 현황", f"현금 실현율 {realized_ratio:.0f}% — {'회수 진행 중' if realized_ratio > 30 else '초기 투자 단계, 미실현 가치 위주'}"))

    label_w = Inches(1.5)
    val_w = Inches(10.5)
    for i, (label, value) in enumerate(es_items):
        row_y = es_y + Inches(i * 0.45)
        bg_c = C_XPALE if i % 2 == 0 else C_WHITE
        _shape(s, M_LEFT, row_y, label_w, Inches(0.38), C_PRIMARY)
        _txt(s, M_LEFT + Inches(0.1), row_y + Inches(0.07), label_w - Inches(0.2), Inches(0.24),
             label, sz=9, color=C_WHITE, bold=True)
        _shape(s, M_LEFT + label_w, row_y, val_w, Inches(0.38), bg_c, C_BORDER)
        _txt(s, M_LEFT + label_w + Inches(0.15), row_y + Inches(0.07), val_w - Inches(0.3), Inches(0.24),
             value, sz=9, color=C_DARK)

    # 하단 핵심 인사이트
    es_bot = es_y + Inches(len(es_items) * 0.45) + Inches(0.15)
    es_insights = []
    if moic >= 2.0 and avg_irr >= 15:
        es_insights.append("펀드 전체 성과가 MOIC·IRR 벤치마크를 모두 달성하여 우수한 수준입니다.")
    elif moic >= 2.0:
        es_insights.append(f"MOIC {moic}x로 벤치마크를 달성했으나, IRR은 목표 대비 {15-avg_irr:.1f}%p 부족합니다.")
    else:
        es_insights.append(f"현재 MOIC {moic}x로 벤치마크(2.0x) 대비 {moic/2.0*100:.0f}% 수준이며, 추가 성장이 필요합니다.")
    es_insights.append(f"전체 {n_cos}개 기업 중 {bm_over}개사가 BM을 달성하여 펀드 수익을 견인하고 있습니다.")
    if bm_under > 0:
        es_insights.append(f"원금 미달 {bm_under}개사에 대한 집중 모니터링 및 Exit 전략 수립이 필요합니다.")
    _insight_panel(s, M_LEFT, es_bot, C_WIDTH, Inches(1.2), "EXECUTIVE INSIGHT", es_insights)

    slide_labels.append("Executive Summary")

    # ════════════════════════════════════════════════
    # 3. Agenda
    # ════════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s, C_WHITE)

    # 좌측: "Agenda" 타이틀 (세로 중앙)
    _txt(s, Inches(1.5), Inches(2.8), Inches(4), Inches(0.8),
         "Agenda", sz=40, color=C_DARK, bold=True)

    # 세로 구분선 (중앙)
    _shape(s, Inches(5.8), Inches(1.2), Pt(1.5), Inches(5.2), C_LGREY)

    # 우측: 목차 항목 (세로 중앙 정렬)
    agenda = ["펀드 성과 종합", "포트폴리오 · 섹터 분석", "Top/Bottom · 리스크",
              "J-Curve · 시나리오 · Sensitivity", "Waterfall 분배",
              "KVIC 시장 비교 · 거시지표", "AI 코멘터리"]
    agenda_keys = [["성과"], ["포트폴리오", "섹터"], ["Top", "리스크"],
                    ["J-Curve", "시나리오", "Sensitivity"], ["Waterfall"],
                    ["KVIC", "거시", "DART"], ["AI"]]
    n_items = len(agenda)
    item_h = 0.55
    total_h = n_items * item_h
    start_y = (7.5 - total_h) / 2
    for i, item in enumerate(agenda):
        keys = agenda_keys[i] if i < len(agenda_keys) else [item.split()[0]]
        active = any(any(k in sn for k in keys) for sn in (selected_sections or []))
        y = Inches(start_y + i * item_h)
        _txt(s, Inches(6.5), y, Inches(0.5), Inches(0.35),
             f"{i + 1}.", sz=14, color=C_DARK if active else C_LGREY,
             bold=active, align=PP_ALIGN.RIGHT)
        _txt(s, Inches(7.1), y, Inches(5), Inches(0.35),
             item, sz=14, color=C_DARK if active else C_LGREY, bold=active)
    slide_labels.append("Agenda")

    # ════════════════════════════════════════════════
    # 3. 성과 요약
    # ════════════════════════════════════════════════
    if _sec("성과 요약"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        bm_msg = f"MOIC {moic}x · IRR {avg_irr}% — {'벤치마크(MOIC 2.0x, IRR 15%) 달성' if moic >= 2.0 and avg_irr >= 15 else '벤치마크 대비 성장 중'}"
        _header(s, "PERFORMANCE SUMMARY", "성과 요약", bm_msg)

        # ── ROW 1: 핵심 KPI 4개 ──
        r1 = BODY_Y + Inches(0.10)
        kpi_w = Inches(2.85); kpi_gap = Inches(0.15)
        for i, (lab, val, sub, vc) in enumerate([
            ("MOIC", f"{moic}x", "투자 대비 전체 가치", C_PRIMARY),
            ("IRR (평균)", f"{avg_irr}%", "연환산 수익률", C_PRIMARY),
            ("TVPI", f"{tvpi}x", "DPI + RVPI", C_PRIMARY if tvpi >= 2.0 else C_BLACK),
            ("투자기업 수", f"{n_cos}개", f"총 {total_inv:,}백만원", C_PRIMARY),
        ]):
            x = M_LEFT + (kpi_w + kpi_gap) * i
            _kpi_card(s, x, r1, kpi_w, Inches(0.95), lab, val, sub, vc)

        # 지표 정의 한 줄
        _txt(s, M_LEFT, r1 + Inches(1.00), C_WIDTH, Inches(0.16),
             "MOIC = 총가치/투자금  ·  IRR = 연환산수익률  ·  TVPI = DPI+RVPI  ·  DPI = 회수금/투자금  ·  RVPI = 미실현/투자금",
             sz=7, color=C_LGREY)

        # ── ROW 2: 가치 흐름 (투자→가치→회수→수익) ──
        r2 = r1 + Inches(1.25)
        _txt(s, M_LEFT, r2, Inches(5), Inches(0.18),
             "VALUE CREATION FLOW", sz=9, color=C_GREY, bold=True)

        total_cur = result_df["현재가치_백만원"].sum()
        total_rec = result_df["회수금액_백만원"].sum()
        total_profit = (total_cur + total_rec) - total_inv
        profit_pct = total_profit / total_inv * 100 if total_inv > 0 else 0

        flow_items = [
            ("투자금", f"{total_inv:,.0f}M", f"{n_cos}개사에 집행", C_DARK),
            ("현재가치", f"{total_cur:,.0f}M", f"미실현 NAV", C_ACCENT),
            ("회수금", f"{total_rec:,.0f}M", f"현금 실현", C_PRIMARY),
            ("수익", f"{total_profit:+,.0f}M", f"수익률 {profit_pct:+.0f}%", C_PRIMARY if total_profit >= 0 else C_RED),
        ]
        fw = Inches(2.65)
        arrow_w = Inches(0.35)
        for i, (fl, fv, fd, fc) in enumerate(flow_items):
            fx = M_LEFT + i * (fw + arrow_w)
            _shape(s, fx, r2 + Inches(0.25), fw, Inches(0.70), C_WHITE, C_BORDER, radius=True)
            _txt(s, fx, r2 + Inches(0.28), fw, Inches(0.15), fl, sz=8, color=C_GREY, bold=True, align=PP_ALIGN.CENTER)
            _txt(s, fx, r2 + Inches(0.45), fw, Inches(0.25), fv, sz=16, color=fc, bold=True, align=PP_ALIGN.CENTER)
            _txt(s, fx, r2 + Inches(0.72), fw, Inches(0.15), fd, sz=7, color=C_GREY, align=PP_ALIGN.CENTER)
            if i < 3:
                ax = fx + fw + Inches(0.05)
                _txt(s, ax, r2 + Inches(0.42), Inches(0.25), Inches(0.25), "→", sz=16, color=C_LGREY, bold=True, align=PP_ALIGN.CENTER)

        # ── ROW 3: 좌측(DPI/RVPI + 벤치마크) / 우측(등급분포 + 인사이트) ──
        r3 = r2 + Inches(1.25)
        half = Inches(5.85)

        # 좌측: DPI/RVPI 분해 + 벤치마크 바
        _kpi_card(s, M_LEFT, r3, Inches(2.8), Inches(0.75), "DPI (현금회수)", f"{dpi}x", "회수금 / 투자금", C_PRIMARY)
        _kpi_card(s, M_LEFT + Inches(2.95), r3, Inches(2.8), Inches(0.75), "RVPI (잔존가치)", f"{rvpi}x", "미실현 / 투자금", C_ACCENT)

        bm_y = r3 + Inches(0.95)
        _txt(s, M_LEFT, bm_y, half, Inches(0.18), "벤치마크 달성률", sz=9, color=C_GREY, bold=True)
        for j, (nm, act, tgt) in enumerate([("MOIC", float(moic), 2.0), ("IRR", float(avg_irr), 15.0), ("TVPI", float(tvpi), 2.0)]):
            by = bm_y + Inches(0.22) + Inches(j * 0.25)
            _txt(s, M_LEFT, by, Inches(0.6), Inches(0.20), nm, sz=9, color=C_BLACK, bold=True)
            pct = min(act / tgt, 1.5) / 1.5
            _bar_h(s, M_LEFT + Inches(0.65), by + Inches(0.03), Inches(3.6), Inches(0.15), pct)
            clr = C_PRIMARY if act >= tgt else C_RED
            _txt(s, M_LEFT + Inches(4.35), by, Inches(0.6), Inches(0.20), f"{act}", sz=9, color=clr, bold=True)
            _txt(s, M_LEFT + Inches(4.95), by, Inches(0.6), Inches(0.20), f"/ {tgt}", sz=8, color=C_GREY)

        # 우측: 포트폴리오 등급 분포
        rx = M_LEFT + Inches(6.3)
        rw = Inches(5.8)
        _txt(s, rx, r3, rw, Inches(0.18), "포트폴리오 등급 분포", sz=9, color=C_GREY, bold=True)

        grade_counts = {"S (3.0x↑)": 0, "A (2.0x)": 0, "B (1.5x)": 0, "C (1.0x)": 0, "D (<1.0x)": 0}
        for m in result_df["MOIC"]:
            if m >= 3.0: grade_counts["S (3.0x↑)"] += 1
            elif m >= 2.0: grade_counts["A (2.0x)"] += 1
            elif m >= 1.5: grade_counts["B (1.5x)"] += 1
            elif m >= 1.0: grade_counts["C (1.0x)"] += 1
            else: grade_counts["D (<1.0x)"] += 1

        gcolors = [C_PRIMARY, C_SECONDARY, C_ACCENT, C_ORANGE, C_RED]
        for gi, ((gname, gcnt), gclr) in enumerate(zip(grade_counts.items(), gcolors)):
            gx = rx + Inches(gi * 1.15)
            _shape(s, gx, r3 + Inches(0.22), Inches(1.05), Inches(0.50), C_WHITE, C_BORDER, radius=True)
            _txt(s, gx, r3 + Inches(0.24), Inches(1.05), Inches(0.15), gname, sz=7, color=C_GREY, align=PP_ALIGN.CENTER)
            _txt(s, gx, r3 + Inches(0.40), Inches(1.05), Inches(0.22), f"{gcnt}개사", sz=11, color=gclr, bold=True, align=PP_ALIGN.CENTER)

        # 우측 하단: KEY INSIGHT
        moic_over2 = len(result_df[result_df["MOIC"] >= 2.0])
        moic_under1 = len(result_df[result_df["MOIC"] < 1.0])
        realized_ratio = total_rec / (total_cur + total_rec) * 100 if (total_cur + total_rec) > 0 else 0

        insights = []
        if moic >= 2.0:
            insights.append(f"MOIC {moic}x로 벤치마크(2.0x) 달성 — 상위 펀드 수준")
        else:
            insights.append(f"MOIC {moic}x — 벤치마크 대비 {moic/2.0*100:.0f}% 달성, {2.0-moic:.2f}x 추가 성장 필요")
        insights.append(f"투자 {total_inv:,.0f}M → 가치 {total_cur+total_rec:,.0f}M 창출 (수익률 {profit_pct:+.0f}%)")
        insights.append(f"현금 실현율 {realized_ratio:.0f}% — {'회수 진행 중' if realized_ratio > 30 else '초기 투자 단계, 미실현 가치 위주'}")
        insights.append(f"BM 달성 {moic_over2}개사 / 원금 미달 {moic_under1}개사 — 전체 {n_cos}개 포트폴리오")
        _insight_panel(s, rx, r3 + Inches(0.85), rw, Inches(1.15), "KEY INSIGHT", insights)

        slide_labels.append("성과")

    # ════════════════════════════════════════════════
    # 4. 포트폴리오 상세
    # ════════════════════════════════════════════════
    if _sec("포트폴리오"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        top1 = result_df.sort_values("MOIC", ascending=False).iloc[0]
        bot1 = result_df.sort_values("MOIC", ascending=True).iloc[0]
        _header(s, "PORTFOLIO DETAIL", "포트폴리오 상세",
                f'{n_cos}개 포트폴리오 기업 중 {top1["회사명"]}이 MOIC {top1["MOIC"]}x로 가장 높은 성과를 보이고 있습니다.')

        # 전체 테이블 (최대 10개사)
        sorted_df = result_df.sort_values("MOIC", ascending=False).head(10)
        hdrs = ["회사명", "섹터", "투자단계", "투자(M)", "현재가치(M)", "회수(M)", "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
        cw = [Inches(1.3), Inches(0.9), Inches(0.75), Inches(0.85), Inches(0.95), Inches(0.85),
              Inches(0.65), Inches(0.7), Inches(0.55), Inches(0.55), Inches(0.55)]
        rows = []
        for _, r in sorted_df.iterrows():
            rows.append([
                r["회사명"], r.get("섹터", "-"), r.get("투자단계", "-"),
                f'{int(r["투자금액_백만원"]):,}', f'{int(r["현재가치_백만원"]):,}',
                f'{int(r["회수금액_백만원"]):,}',
                f'{r["MOIC"]}x', f'{r["IRR(%)"]}%',
                f'{r["DPI"]}x', f'{r["RVPI"]}x', f'{r["TVPI"]}x',
            ])
        _table(s, M_LEFT, BODY_Y, hdrs, rows, cw, Inches(0.28))

        # 우측에 차트 (테이블 아래 또는 옆)
        chart_y = BODY_Y + Inches(0.28) * (len(rows) + 1) + Inches(0.15)
        if include_charts:
            import plotly.graph_objects as go
            sd = result_df.sort_values("MOIC", ascending=True)
            fig = go.Figure(go.Bar(
                x=sd["MOIC"].tolist(), y=sd["회사명"].tolist(), orientation="h",
                marker_color=["rgba(27,94,32,0.7)" if m >= 2 else "rgba(67,160,71,0.5)" if m >= 1 else "rgba(198,40,40,0.4)" for m in sd["MOIC"]],
                text=[f"{m}x" for m in sd["MOIC"]], textposition="outside", textfont=dict(size=8),
                marker_line_width=0,
            ))
            fig.add_vline(x=2.0, line_dash="dot", line_color="#999", annotation_text="BM 2.0x", annotation_font_size=8)
            fig.update_layout(height=220, width=550, margin=dict(t=5, b=10, l=70, r=30),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(showgrid=True, gridcolor="#eee"), yaxis=dict(showgrid=False), bargap=0.25)
            _chart_img(s, fig, 0.6, min(float(chart_y / 914400), 5.0), 6.0, 2.5)

        # 인사이트 (테이블 아래 우측)
        moic_over2 = len(result_df[result_df["MOIC"] >= 2.0])
        moic_under1 = len(result_df[result_df["MOIC"] < 1.0])
        avg_moic = result_df["MOIC"].mean()
        med_moic = result_df["MOIC"].median()
        top_name = result_df.sort_values("MOIC", ascending=False).iloc[0]["회사명"]
        top_moic = result_df.sort_values("MOIC", ascending=False).iloc[0]["MOIC"]
        ins = [
            f"BM 달성(≥2.0x): {moic_over2}개사 ({moic_over2/n_cos*100:.0f}%) — 포트폴리오 {n_cos}개 중",
            f"원금 미회수(<1.0x): {moic_under1}개사 — {'리스크 관리 필요' if moic_under1 > 0 else '전 기업 원금 이상'}",
            f"평균 MOIC {avg_moic:.2f}x / 중앙값 {med_moic:.2f}x — {'상위 집중' if avg_moic > med_moic * 1.2 else '균등 분포'}",
            f"최고 성과: {top_name} ({top_moic}x) — 펀드 전체 수익의 핵심 드라이버",
        ]
        ins_y = min(float(chart_y / 914400), 4.8)
        _insight_panel(s, Inches(6.8), Inches(ins_y), Inches(5.9), Inches(1.3), "PORTFOLIO INSIGHT", ins)
        slide_labels.append("포트폴리오")

    # ════════════════════════════════════════════════
    # 5. 섹터 분석
    # ════════════════════════════════════════════════
    if _sec("섹터") and "섹터" in result_df.columns:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        sa = result_df.groupby("섹터").agg(
            기업수=("회사명", "count"), 총투자=("투자금액_백만원", "sum"),
            평균MOIC=("MOIC", "mean"), 평균IRR=("IRR(%)", "mean")
        ).sort_values("총투자", ascending=False).reset_index()
        total_all = sa["총투자"].sum()
        top_sec = sa.iloc[0]
        best_moic_sec = sa.sort_values("평균MOIC", ascending=False).iloc[0]
        top3_pct = sa.head(3)["총투자"].sum() / total_all * 100
        _header(s, "SECTOR ANALYSIS", "섹터별 투자 분석",
                f"총 {len(sa)}개 섹터에 분산 투자하며, {top_sec['섹터']}에 전체의 {top_sec['총투자']/total_all*100:.0f}%가 집중되어 있습니다.")

        # ── 페이지 1: 테이블 ──
        sec_hdrs = ["섹터", "기업수", "투자(M)", "비중", "MOIC", "IRR"]
        sec_cw = [Inches(1.1), Inches(0.55), Inches(0.9), Inches(0.6), Inches(0.7), Inches(0.7)]
        sec_rows = []
        for _, r in sa.head(8).iterrows():
            pct = r["총투자"] / total_all * 100 if total_all > 0 else 0
            sec_rows.append([r["섹터"], f'{int(r["기업수"])}', f'{int(r["총투자"]):,}',
                             f'{pct:.0f}%', f'{r["평균MOIC"]:.1f}x', f'{r["평균IRR"]:.0f}%'])
        _table(s, M_LEFT, BODY_Y, sec_hdrs, sec_rows, sec_cw, Inches(0.32))

        # 우측: Plotly 바 차트 — 테이블 오른쪽에 배치 (겹침 방지)
        chart_x = 5.5
        if include_charts:
            import plotly.graph_objects as go
            sa_plot = sa.head(6).sort_values("총투자", ascending=True)
            fig = go.Figure(go.Bar(
                x=sa_plot["총투자"].tolist(), y=sa_plot["섹터"].tolist(), orientation="h",
                marker_color=["#1b5e20", "#2e7d32", "#43a047", "#66bb6a", "#a5d6a7", "#c8e6c9"][:len(sa_plot)],
                text=[f'{int(v):,}M ({v/total_all*100:.0f}%)' for v in sa_plot["총투자"]],
                textposition="outside", textfont=dict(size=8), marker_line_width=0,
            ))
            fig.update_layout(height=250, width=480, margin=dict(t=5, b=25, l=80, r=70),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(showgrid=True, gridcolor="#eee", title="투자금(백만원)"),
                              yaxis=dict(showgrid=False), bargap=0.3)
            _chart_img(s, fig, chart_x, float(BODY_Y / 914400) + 0.2, 4.8, 3.0)

        # 하단 요약 텍스트 (잘리지 않게)
        sec_sum_y = BODY_Y + Inches(3.8)
        _txt(s, M_LEFT, sec_sum_y, C_WIDTH, Inches(0.20),
             f"총 {len(sa)}개 섹터에 {n_cos}개 기업이 분산 투자되어 있으며, 상위 3개 섹터가 전체 투자금의 {top3_pct:.0f}%를 차지합니다.",
             sz=10, color=C_DARK)
        slide_labels.append("섹터")

        # ── 페이지 2: 섹터 심층 분석 ──
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "SECTOR DEEP DIVE", "섹터 심층 분석",
                f"{best_moic_sec['섹터']} 섹터가 평균 MOIC {best_moic_sec['평균MOIC']:.1f}x로 가장 높은 수익률을 보이고 있습니다.")

        # 좌측: 분석 과정
        _txt(s, M_LEFT, BODY_Y, Inches(5), Inches(0.20), "SECTOR ANALYSIS PROCESS", sz=10, color=C_GREY, bold=True)
        process_items = [
            f"① 투자 분산 현황: {len(sa)}개 섹터에 {n_cos}개 기업 배분",
            f"② 집중도 분석: 상위 3개 섹터({', '.join(sa.head(3)['섹터'].tolist())})가 전체의 {top3_pct:.0f}%를 차지",
            f"③ 성과 비교: {best_moic_sec['섹터']} 섹터가 평균 MOIC {best_moic_sec['평균MOIC']:.1f}x, IRR {best_moic_sec['평균IRR']:.0f}%로 최고 성과",
            f"④ 최대 투자 섹터: {top_sec['섹터']}에 {top_sec['총투자']:,.0f}M ({top_sec['총투자']/total_all*100:.0f}%) 집중",
            f"⑤ 분산 평가: {'분산 양호 — 개별 섹터 부진 시에도 포트폴리오 전체 영향 제한적' if len(sa) >= 4 else '분산 부족 — 추가 섹터 다변화를 통한 리스크 분산 필요'}",
        ]
        _multiline(s, M_LEFT, BODY_Y + Inches(0.30), Inches(5.8), Inches(1.8), process_items, sz=10, color=C_DARK, spacing=7)

        # 우측: 섹터별 성과 비교 KPI
        rx = M_LEFT + Inches(6.3)
        _txt(s, rx, BODY_Y, Inches(5), Inches(0.20), "섹터별 성과 비교", sz=10, color=C_GREY, bold=True)
        for i, (_, r) in enumerate(sa.head(4).iterrows()):
            cy = BODY_Y + Inches(0.30) + Inches(i * 0.45)
            pct = r["총투자"] / total_all if total_all > 0 else 0
            _shape(s, rx, cy, Inches(5.8), Inches(0.38), C_WHITE, C_BORDER, radius=True)
            _txt(s, rx + Inches(0.1), cy + Inches(0.07), Inches(1.2), Inches(0.24),
                 r["섹터"], sz=10, color=C_BLACK, bold=True)
            _bar_h(s, rx + Inches(1.4), cy + Inches(0.10), Inches(2.0), Inches(0.15), pct)
            _txt(s, rx + Inches(3.5), cy + Inches(0.07), Inches(0.7), Inches(0.24),
                 f'{pct*100:.0f}%', sz=9, color=C_PRIMARY, bold=True)
            _txt(s, rx + Inches(4.2), cy + Inches(0.07), Inches(1.5), Inches(0.24),
                 f'MOIC {r["평균MOIC"]:.1f}x · IRR {r["평균IRR"]:.0f}%', sz=8, color=C_DARK)

        # 하단: 인사이트
        sec_ins = [
            f"최대 투자 섹터 {top_sec['섹터']}에 {top_sec['총투자']/total_all*100:.0f}% 집중 — {'과도한 편중으로 분산 필요' if top_sec['총투자']/total_all > 0.4 else '적정 수준의 집중도'}",
            f"최고 수익 섹터 {best_moic_sec['섹터']}는 MOIC {best_moic_sec['평균MOIC']:.1f}x, IRR {best_moic_sec['평균IRR']:.0f}%로 펀드 수익을 견인합니다.",
            f"{'투자 대비 성과가 낮은 섹터에 대한 후속 투자 검토 및 Exit 전략 수립이 필요합니다.' if sa.iloc[-1]['평균MOIC'] < 1.5 else '전반적으로 섹터별 성과가 양호한 수준입니다.'}",
        ]
        _insight_panel(s, M_LEFT, BODY_Y + Inches(2.5), C_WIDTH, Inches(1.3), "SECTOR INSIGHT", sec_ins)
        slide_labels.append("섹터 심층")

    # ════════════════════════════════════════════════
    # 6. Top / Bottom
    # ════════════════════════════════════════════════
    if _sec("Top/Bottom"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        sd = result_df.sort_values("MOIC", ascending=False)
        _top_gap = sd.iloc[0]["MOIC"] - sd.iloc[-1]["MOIC"]
        _header(s, "TOP / BOTTOM", "성과 상위 · 하위 분석",
                f'{sd.iloc[0]["회사명"]}이 MOIC {sd.iloc[0]["MOIC"]}x로 최고 성과를 기록하였으며, 상하위 간 {_top_gap:.1f}x의 격차가 존재합니다.')

        half_w = Inches(5.85)
        # 좌측: Top 3
        _shape(s, M_LEFT, BODY_Y, half_w, Inches(0.28), C_PRIMARY)
        _txt(s, M_LEFT + Inches(0.1), BODY_Y + Inches(0.04), Inches(3), Inches(0.2),
             "▲ TOP PERFORMERS", sz=9, color=C_WHITE, bold=True)
        for i, (_, r) in enumerate(sd.head(3).iterrows()):
            y = BODY_Y + Inches(0.35) + Inches(i * 0.75)
            _shape(s, M_LEFT, y, half_w, Inches(0.65), C_WHITE, C_BORDER, radius=True)
            _shape(s, M_LEFT + Inches(0.1), y + Inches(0.12), Inches(0.35), Inches(0.35), C_PRIMARY, radius=True)
            _txt(s, M_LEFT + Inches(0.1), y + Inches(0.15), Inches(0.35), Inches(0.3),
                 str(i + 1), sz=12, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
            _txt(s, M_LEFT + Inches(0.55), y + Inches(0.08), Inches(2.0), Inches(0.2),
                 r["회사명"], sz=13, color=C_BLACK, bold=True)
            _txt(s, M_LEFT + Inches(0.55), y + Inches(0.32), Inches(2.0), Inches(0.18),
                 f'{r.get("섹터", "")} · {r.get("투자단계", "")}', sz=8, color=C_GREY)
            _txt(s, M_LEFT + Inches(3.0), y + Inches(0.12), Inches(1.0), Inches(0.2),
                 f'MOIC {r["MOIC"]}x', sz=12, color=C_PRIMARY, bold=True)
            _txt(s, M_LEFT + Inches(4.1), y + Inches(0.12), Inches(0.8), Inches(0.2),
                 f'IRR {r["IRR(%)"]}%', sz=10, color=C_DARK)
            _txt(s, M_LEFT + Inches(4.9), y + Inches(0.12), Inches(0.8), Inches(0.2),
                 f'TVPI {r["TVPI"]}x', sz=10, color=C_DARK)

        # 우측: Bottom 3
        rx = M_LEFT + half_w + Inches(0.43)
        _shape(s, rx, BODY_Y, half_w, Inches(0.28), C_RED)
        _txt(s, rx + Inches(0.1), BODY_Y + Inches(0.04), Inches(3), Inches(0.2),
             "▼ UNDERPERFORMERS", sz=9, color=C_WHITE, bold=True)
        for i, (_, r) in enumerate(sd.tail(3).iterrows()):
            y = BODY_Y + Inches(0.35) + Inches(i * 0.75)
            clr = C_RED if r["MOIC"] < 1.0 else C_GREY
            _shape(s, rx, y, half_w, Inches(0.65), C_WHITE, C_BORDER, radius=True)
            _shape(s, rx + Inches(0.1), y + Inches(0.12), Inches(0.35), Inches(0.35), clr, radius=True)
            _txt(s, rx + Inches(0.1), y + Inches(0.15), Inches(0.35), Inches(0.3),
                 str(i + 1), sz=12, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
            _txt(s, rx + Inches(0.55), y + Inches(0.08), Inches(2.0), Inches(0.2),
                 r["회사명"], sz=13, color=C_BLACK, bold=True)
            _txt(s, rx + Inches(0.55), y + Inches(0.32), Inches(2.0), Inches(0.18),
                 f'{r.get("섹터", "")} · {r.get("투자단계", "")}', sz=8, color=C_GREY)
            _txt(s, rx + Inches(3.0), y + Inches(0.12), Inches(1.0), Inches(0.2),
                 f'MOIC {r["MOIC"]}x', sz=12, color=clr, bold=True)
            _txt(s, rx + Inches(4.1), y + Inches(0.12), Inches(0.8), Inches(0.2),
                 f'IRR {r["IRR(%)"]}%', sz=10, color=C_DARK)
            _txt(s, rx + Inches(4.9), y + Inches(0.12), Inches(0.8), Inches(0.2),
                 f'TVPI {r["TVPI"]}x', sz=10, color=C_DARK)

        # 하단: 분석 과정 + 인사이트 (차트 없이 텍스트로 — 겹침 방지)
        tb_bot = BODY_Y + Inches(3.0)
        _txt(s, M_LEFT, tb_bot, Inches(4), Inches(0.18), "ANALYSIS", sz=9, color=C_GREY, bold=True)
        tb_process = [
            f"① MOIC 기준 전체 {n_cos}개사를 정렬하여 상위 3개와 하위 3개를 추출",
            f"② 상위 3개 평균 MOIC {sd.head(3)['MOIC'].mean():.1f}x vs 하위 3개 {sd.tail(3)['MOIC'].mean():.1f}x — 격차 {sd.head(3)['MOIC'].mean()-sd.tail(3)['MOIC'].mean():.1f}x",
            f"③ 원금 미달(MOIC<1.0x) {len(sd[sd['MOIC']<1.0])}개사 → {'리스크 관리 필요' if len(sd[sd['MOIC']<1.0]) > 0 else '전 기업 원금 이상'}",
            f"④ 성과 편차(표준편차 {result_df['MOIC'].std():.2f}) — {'분산 큼, 상위 기업 의존도 높음' if result_df['MOIC'].std() > 1.0 else '안정적 분포'}",
        ]
        _multiline(s, M_LEFT, tb_bot + Inches(0.22), Inches(5.5), Inches(1.2), tb_process, sz=9, color=C_DARK, spacing=5)

        tb_ins = [
            f"상위 기업이 펀드 수익을 견인하고 있으며, 하위 기업의 Exit 전략 재검토가 필요합니다.",
            f"{'원금 미달 기업에 대한 집중 모니터링이 시급합니다.' if len(sd[sd['MOIC']<1.0]) > 0 else '전 기업이 원금 이상을 유지하고 있어 안정적입니다.'}",
        ]
        _insight_panel(s, Inches(6.3), tb_bot, Inches(6.4), Inches(1.3), "PERFORMANCE GAP", tb_ins)
        slide_labels.append("Top/Bottom")

    # ════════════════════════════════════════════════
    # 7. 리스크 · 집중도
    # ════════════════════════════════════════════════
    if _sec("리스크") or _sec("집중도"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        weights = result_df["투자금액_백만원"] / result_df["투자금액_백만원"].sum()
        hhi = round((weights ** 2).sum() * 10000)
        hhi_label = "HIGH" if hhi > 2500 else ("MEDIUM" if hhi > 1500 else "LOW")
        n_under = len(result_df[result_df["MOIC"] < 1.0])
        _header(s, "RISK & CONCENTRATION", "리스크 · 집중도 평가",
                f'포트폴리오 집중도(HHI)는 {hhi:,}으로 {hhi_label} 수준이며, 원금 미달 기업은 {n_under}개사입니다.')

        # 좌측: 리스크 항목
        risks = []
        under = result_df[result_df["MOIC"] < 1.0]
        if len(under) > 0:
            risks.append(("원금 손실 위험", f"MOIC<1.0x: {', '.join(under['회사명'].tolist())}", "HIGH"))
        if hhi > 2500:
            risks.append(("집중 리스크", f"HHI {hhi:,} — 특정 기업에 투자 편중", "HIGH"))
        elif hhi > 1500:
            risks.append(("집중도 보통", f"HHI {hhi:,} — 분산 확대 검토 필요", "MEDIUM"))
        else:
            risks.append(("분산 양호", f"HHI {hhi:,} — 적정 분산 수준", "LOW"))
        if dpi < 0.5:
            risks.append(("회수 지연", f"DPI {dpi}x — 현금 회수 제한적", "MEDIUM"))
        if moic >= 2.0:
            risks.append(("우수 성과", f"MOIC {moic}x — 벤치마크 달성", "POSITIVE"))

        # ── 좌측: 리스크 항목 (간격 줄임) ──
        left_w = Inches(5.85)
        _txt(s, M_LEFT, BODY_Y, Inches(3), Inches(0.18), "리스크 항목 평가", sz=9, color=C_GREY, bold=True)
        for i, (title, desc, level) in enumerate(risks):
            y = BODY_Y + Inches(0.22) + Inches(i * 0.52)
            if level == "HIGH":
                icon_c, bg_c, bd_c = C_RED, RGBColor(0xFE, 0xF5, 0xF5), RGBColor(0xF0, 0xD0, 0xD0)
            elif level == "MEDIUM":
                icon_c, bg_c, bd_c = C_ORANGE, RGBColor(0xFF, 0xF8, 0xEE), RGBColor(0xF0, 0xE0, 0xC0)
            else:
                icon_c, bg_c, bd_c = C_PRIMARY, C_XPALE, C_PALE
            _shape(s, M_LEFT, y, left_w, Inches(0.44), bg_c, bd_c, radius=True)
            _shape(s, M_LEFT + Inches(0.10), y + Inches(0.07), Inches(0.28), Inches(0.28), icon_c, radius=True)
            icon_txt = "!" if level in ("HIGH", "MEDIUM") else "✓"
            _txt(s, M_LEFT + Inches(0.10), y + Inches(0.08), Inches(0.28), Inches(0.26),
                 icon_txt, sz=9, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
            _txt(s, M_LEFT + Inches(0.50), y + Inches(0.05), Inches(2.5), Inches(0.18),
                 title, sz=10, color=C_BLACK, bold=True)
            _txt(s, M_LEFT + Inches(0.50), y + Inches(0.24), left_w - Inches(0.65), Inches(0.16),
                 desc, sz=8, color=C_DARK)

        # ── 우측: KPI 3개 (한 행) ──
        rx = M_LEFT + Inches(6.3)
        realized_pct = round(result_df["회수금액_백만원"].sum() / total_val * 100, 1) if total_val > 0 else 0
        avg_days = 0
        if "투자일" in result_df.columns:
            try:
                avg_days = (pd.to_datetime(result_df.iloc[0].get("기준일", datetime.date.today())) - pd.to_datetime(result_df["투자일"].min())).days
            except Exception:
                pass
        avg_yrs = round(avg_days / 365.25, 1) if avg_days > 0 else 0

        _kpi_card(s, rx, BODY_Y, Inches(1.85), Inches(0.80), "HHI", f"{hhi:,}", hhi_label,
                  C_RED if hhi > 2500 else C_ORANGE if hhi > 1500 else C_PRIMARY)
        _kpi_card(s, rx + Inches(1.95), BODY_Y, Inches(1.85), Inches(0.80), "실현율", f"{realized_pct}%", "회수/전체가치",
                  C_PRIMARY if realized_pct > 50 else C_BLACK)
        _kpi_card(s, rx + Inches(3.90), BODY_Y, Inches(1.85), Inches(0.80), "보유기간", f"{avg_yrs}년", "최초투자~기준일", C_BLACK)

        # 우측: 투자단계 분포 (KPI 바로 아래)
        if "투자단계" in result_df.columns:
            _txt(s, rx, BODY_Y + Inches(0.95), Inches(5.8), Inches(0.18), "투자단계 분포", sz=9, color=C_GREY, bold=True)
            stage_cnt = result_df["투자단계"].value_counts()
            for j, (stage, cnt) in enumerate(stage_cnt.items()):
                if j >= 4: break
                sx = rx + Inches(j * 1.45)
                _shape(s, sx, BODY_Y + Inches(1.15), Inches(1.35), Inches(0.42), C_XPALE, C_PALE, radius=True)
                _txt(s, sx, BODY_Y + Inches(1.17), Inches(1.35), Inches(0.16), stage, sz=9, color=C_PRIMARY, bold=True, align=PP_ALIGN.CENTER)
                _txt(s, sx, BODY_Y + Inches(1.34), Inches(1.35), Inches(0.18), f"{cnt}개사 ({cnt/n_cos*100:.0f}%)", sz=8, color=C_DARK, align=PP_ALIGN.CENTER)

        # ── 하단: 분석 과정(좌) + 인사이트(우) ──
        risk_bot = BODY_Y + Inches(2.8)
        _txt(s, M_LEFT, risk_bot, Inches(3), Inches(0.18), "ANALYSIS", sz=9, color=C_GREY, bold=True)
        risk_process = [
            f"① HHI 산출: 투자비중 제곱합 × 10,000 = {hhi:,} → {hhi_label}",
            f"② 실현율: 회수 {result_df['회수금액_백만원'].sum():,.0f}M / 전체 {total_val:,.0f}M = {realized_pct}%",
            f"③ MOIC<1.0x 스크리닝: {len(under)}개사 → {'모니터링 대상' if len(under) > 0 else '해당 없음'}",
        ]
        _multiline(s, M_LEFT, risk_bot + Inches(0.20), Inches(5.5), Inches(0.9), risk_process, sz=9, color=C_DARK, spacing=5)

        risk_ins = [
            f"{'집중도 높음 — 특정 기업 부진 시 펀드 전체에 영향 가능' if hhi > 2500 else '적정 분산 — 개별 기업 리스크 제한적'}",
            f"{'현금 회수 초기 — 미실현 가치 현실화 모니터링 필요' if realized_pct < 30 else '회수 진행 중 — LP 배분 가능성 증가'}",
        ]
        _insight_panel(s, Inches(6.3), risk_bot, Inches(6.4), Inches(1.0), "RISK ASSESSMENT", risk_ins)
        slide_labels.append("리스크")

    # ════════════════════════════════════════════════
    # 8. J-Curve
    # ════════════════════════════════════════════════
    if _sec("J-Curve") and jcurve_df is not None and not jcurve_df.empty:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        mn = jcurve_df["누적현금흐름"].min()
        cr = jcurve_df["누적현금흐름"].iloc[-1]
        be = jcurve_df[jcurve_df["누적현금흐름"] >= 0]
        be_dt = str(be["날짜"].iloc[0])[:10] if not be.empty else "미도달"
        recovery = cr / abs(mn) * 100 if mn != 0 else 0
        _header(s, "J-CURVE ANALYSIS", "J-Curve 현금흐름 분석",
                f'최대 {abs(mn):,.0f}M 투자 후 현재 누적 CF {cr:,.0f}M으로, 회복률은 {recovery:.0f}%입니다.')

        # KPI 4개
        kw = Inches(2.85)
        _kpi_card(s, M_LEFT, BODY_Y, kw, Inches(0.90), "MAX DRAWDOWN", f"{mn:,.0f}M", "최대 누적 투자", C_RED)
        _kpi_card(s, M_LEFT + Inches(3.05), BODY_Y, kw, Inches(0.90), "현재 누적 CF", f"{cr:,.0f}M", "현재 순현금흐름", C_PRIMARY if cr >= 0 else C_RED)
        _kpi_card(s, M_LEFT + Inches(6.10), BODY_Y, kw, Inches(0.90), "회복률", f"{recovery:.0f}%", "현재CF / MaxDD", C_PRIMARY if recovery > 100 else C_ORANGE)
        _kpi_card(s, M_LEFT + Inches(9.15), BODY_Y, kw, Inches(0.90), "손익분기", be_dt, "BEP 달성 시점", C_PRIMARY if be_dt != "미도달" else C_GREY)

        # 차트
        if include_charts:
            import plotly.graph_objects as go
            dates = jcurve_df["날짜"].astype(str).tolist()
            cf = jcurve_df["누적현금흐름"].tolist()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=cf, mode="lines+markers",
                                     line=dict(color="#1b5e20", width=2.5),
                                     fill="tozeroy", fillcolor="rgba(27,94,32,0.08)",
                                     marker=dict(size=5, color=["#1b5e20" if v >= 0 else "#c62828" for v in cf])))
            fig.add_hline(y=0, line_dash="dash", line_color="#999")
            fig.update_layout(height=240, width=650, margin=dict(t=10, b=25, l=50, r=15),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                              xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#eee", title="백만원"))
            _chart_img(s, fig, 0.6, 2.55, 7.0, 2.8)

        # 우측: J-Curve 분석 과정 + 해석
        jc_stage = "투자 집행기" if cr < 0 else ("회수 전환기" if recovery < 100 else "수익 실현기")
        jc_texts = [
            f"① {len(jcurve_df)}건의 현금흐름을 시계열로 누적 산출",
            f"② 최대 누적 손실 {abs(mn):,.0f}M 시점 확인 → 투자 집행 피크",
            f"③ 현재 누적 CF {cr:,.0f}M → 회복률 {recovery:.0f}%",
            f"④ 현재 단계: {jc_stage}",
            f"⑤ 손익분기: {'달성(' + be_dt + ')' if be_dt != '미도달' else '미도달 — 추가 회수 필요'}",
        ]
        _insight_panel(s, Inches(8.0), Inches(2.55), Inches(4.7), Inches(1.5), "J-CURVE 분석 과정", jc_texts)

        # 현금흐름 테이블
        jc_hdrs = ["날짜", "현금흐름(M)", "누적(M)"]
        jc_cw = [Inches(1.2), Inches(1.0), Inches(1.0)]
        jc_rows_data = []
        for _, r in jcurve_df.tail(6).iterrows():
            jc_rows_data.append([str(r["날짜"])[:10], f'{r.get("현금흐름_백만원", 0):,.0f}', f'{r["누적현금흐름"]:,.0f}'])
        if jc_rows_data:
            _table(s, Inches(8.0), Inches(3.95), jc_hdrs, jc_rows_data, jc_cw, Inches(0.25))
        slide_labels.append("J-Curve")

    # ════════════════════════════════════════════════
    # 9. 시나리오 분석
    # ════════════════════════════════════════════════
    if _sec("시나리오") and scenario_df is not None and not scenario_df.empty:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "EXIT SCENARIO", f"회수 시나리오 — {scenario_company}",
                f'{scenario_company}의 Exit 배수별 예상 IRR을 시뮬레이션하여 최적 회수 타이밍을 분석합니다.')

        # 좌측: 차트
        if include_charts and "Exit 배수" in scenario_df.columns and "IRR (%)" in scenario_df.columns:
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(
                x=scenario_df["Exit 배수"].tolist(), y=scenario_df["IRR (%)"].tolist(),
                marker_color=["#1b5e20" if v >= 20 else "#43a047" if v >= 0 else "#c62828" for v in scenario_df["IRR (%)"]],
                text=[f"{v}%" for v in scenario_df["IRR (%)"]], textposition="outside", textfont=dict(size=9),
                marker_line_width=0,
            ))
            fig.add_hline(y=15, line_dash="dot", line_color="#999", annotation_text="Target 15%", annotation_font_size=8)
            fig.update_layout(height=280, width=600, margin=dict(t=10, b=30, l=40, r=15),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False, bargap=0.3,
                              xaxis=dict(showgrid=False, title="Exit 배수"), yaxis=dict(showgrid=True, gridcolor="#eee", title="IRR (%)"))
            _chart_img(s, fig, 0.6, 1.50, 6.5, 3.5)

        # 우측: 시나리오 테이블
        sc_hdrs = ["Exit 배수", "IRR (%)", "회수금액(M)", "판정"]
        sc_cw = [Inches(0.8), Inches(0.8), Inches(1.2), Inches(0.8)]
        sc_rows = []
        for _, r in scenario_df.iterrows():
            irr_val = r.get("IRR (%)", 0)
            verdict = "달성" if irr_val >= 15 else "미달"
            exit_disp = r.get("Exit 배수", "")
            exit_disp = exit_disp if str(exit_disp).endswith(("x", "X")) else f"{exit_disp}x"
            sc_rows.append([exit_disp, f'{irr_val}%',
                            f'{r.get("회수금액 (백만원)", 0):,.0f}', verdict])
        _table(s, Inches(7.5), BODY_Y, sc_hdrs, sc_rows, sc_cw, Inches(0.28))

        # 하단 좌측: 분석 과정
        target_rows = scenario_df[scenario_df["IRR (%)"] >= 15] if "IRR (%)" in scenario_df.columns else pd.DataFrame()

        def _to_num(v):
            try:
                return float(str(v).rstrip("xX"))
            except (ValueError, TypeError):
                return None

        min_exit_val = None
        if not target_rows.empty:
            nums = [n for n in target_rows["Exit 배수"].apply(_to_num) if n is not None]
            min_exit_val = min(nums) if nums else None
        min_exit_disp = f"{min_exit_val}x" if min_exit_val is not None else "N/A"

        max_irr = scenario_df["IRR (%)"].max() if "IRR (%)" in scenario_df.columns else 0
        max_irr_exit = scenario_df.loc[scenario_df['IRR (%)'].idxmax(), 'Exit 배수'] if "IRR (%)" in scenario_df.columns else "-"
        max_irr_exit_disp = max_irr_exit if str(max_irr_exit).endswith(("x", "X")) else f"{max_irr_exit}x"

        sc_bot = Inches(5.2)
        _txt(s, M_LEFT, sc_bot, Inches(3), Inches(0.18), "ANALYSIS", sz=9, color=C_GREY, bold=True)
        sc_process = [
            f"① {scenario_company}의 현재 투자금을 기준으로 {len(scenario_df)}개 Exit 배수 시나리오를 시뮬레이션",
            f"② 목표 IRR 15% 달성을 위해서는 최소 Exit {min_exit_disp} 이상이 필요",
            f"③ 최대 IRR {max_irr}%는 Exit {max_irr_exit_disp} 시나리오에서 달성",
            f"④ Exit 배수가 1.0x 이하인 경우 원금 손실이 발생하므로 최소 1.5x 이상 Exit을 목표로 설정 권장",
        ]
        _multiline(s, M_LEFT, sc_bot + Inches(0.20), Inches(6.0), Inches(1.2), sc_process, sz=9, color=C_DARK, spacing=5)

        # 하단 우측: 인사이트
        min_exit_ok = min_exit_val is not None and min_exit_val <= 2.0
        sc_ins = [
            f"IRR 15% 달성 최소 배수: {min_exit_disp} — {'달성 가능성 높음' if min_exit_ok else '높은 Exit 배수 필요'}",
            f"LP 관점에서 Exit 타이밍과 배수 관리가 펀드 수익률을 결정짓는 핵심 변수입니다.",
        ]
        _insight_panel(s, Inches(6.8), sc_bot, Inches(5.9), Inches(1.0), "SCENARIO INSIGHT", sc_ins)
        slide_labels.append("시나리오")

    # ════════════════════════════════════════════════
    # 10. IRR Sensitivity
    # ════════════════════════════════════════════════
    if _sec("Sensitivity") and sensitivity_df is not None:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "IRR SENSITIVITY", f"IRR Sensitivity — {sensitivity_company}",
                f'{sensitivity_company}의 Exit 배수와 보유기간 조합에 따른 IRR 변동을 매트릭스로 분석합니다.')

        if include_charts:
            import plotly.graph_objects as go
            matrix = sensitivity_df.values.tolist()
            fig = go.Figure(data=go.Heatmap(
                z=matrix, x=list(sensitivity_df.columns), y=list(sensitivity_df.index),
                colorscale=[[0, "#c62828"], [0.15, "#e53935"], [0.3, "#ff9800"], [0.45, "#ffc107"],
                            [0.55, "#cddc39"], [0.7, "#66bb6a"], [0.85, "#43a047"], [1.0, "#1b5e20"]],
                zmid=15, text=[[f"{v}%" for v in row] for row in matrix],
                texttemplate="%{text}", textfont=dict(size=7, color="#fff"),
                showscale=False,
            ))
            fig.update_layout(height=300, width=750, margin=dict(t=10, b=30, l=50, r=15),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis_title="보유기간", yaxis_title="Exit 배수")
            _chart_img(s, fig, 0.6, 1.50, 8.0, 3.8)
        else:
            sens_hdrs = ["Exit\\기간"] + list(sensitivity_df.columns)[:8]
            sens_cw = [Inches(0.8)] + [Inches(0.8)] * min(8, len(sensitivity_df.columns))
            sens_rows = []
            for idx, row in sensitivity_df.iterrows():
                sens_rows.append([str(idx)] + [f"{row[c]}%" for c in list(sensitivity_df.columns)[:8]])
            _table(s, M_LEFT, BODY_Y, sens_hdrs, sens_rows, sens_cw, Inches(0.30))

        # 우측: 컬러 범례 + 해석 (차트 옆이 아닌 오른쪽 상단에 작게)
        _txt(s, Inches(9.0), BODY_Y, Inches(3.7), Inches(0.20), "SENSITIVITY 해석", sz=9, color=C_GREY, bold=True)
        sens_legend = [
            "■ 초록: IRR ≥15% (목표 달성)",
            "■ 노랑: IRR 5~15% (보통)",
            "■ 빨강: IRR <5% (저성과)",
        ]
        _multiline(s, Inches(9.0), BODY_Y + Inches(0.25), Inches(3.7), Inches(0.8), sens_legend, sz=9, color=C_DARK, spacing=5)

        # 하단: 분석 과정 + 인사이트 (차트 아래)
        sens_bot = Inches(5.5)
        sens_process = [
            f"① {sensitivity_company}의 현재 투자금 기준으로 Exit 배수(0.5~5.0x)와 보유기간(1~10년) 조합별 IRR을 산출",
            f"② 목표 IRR 15% 달성 가능 구간을 매트릭스에서 식별 — 초록 영역이 목표 달성 구간",
            f"③ LP 관점 최적 구간: Exit 배수 2.0x 이상 · 보유기간 3~5년이 IRR 극대화에 유리",
        ]
        _multiline(s, M_LEFT, sens_bot, Inches(6.0), Inches(1.0), sens_process, sz=9, color=C_DARK, spacing=5)

        sens_ins = [
            "단기 고배수 Exit이 IRR 극대화에 가장 유리합니다.",
            "장기 보유 시에도 2.0x 이상이면 안정적 수익이 가능합니다.",
        ]
        _insight_panel(s, Inches(6.8), sens_bot, Inches(5.9), Inches(0.85), "SENSITIVITY INSIGHT", sens_ins)
        slide_labels.append("Sensitivity")

    # ════════════════════════════════════════════════
    # 11. Waterfall 분배
    # ════════════════════════════════════════════════
    if _sec("Waterfall"):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        wf_inv = float(total_inv)
        wf_proc = float(result_df["현재가치_백만원"].sum() + result_df["회수금액_백만원"].sum())
        hurdle, carry, years = 8, 20, 5
        profit = max(0, wf_proc - wf_inv)
        hurdle_amt = wf_inv * ((1 + hurdle / 100) ** years - 1)
        rem = wf_proc
        s1 = min(rem, wf_inv); rem -= s1
        s2 = min(rem, hurdle_amt); rem -= s2
        gp_t = profit * carry / 100
        s3_gp = min(rem, gp_t); rem -= s3_gp
        s4_gp = rem * carry / 100; s4_lp = rem - s4_gp
        total_lp = s1 + s2 + s4_lp; total_gp = s3_gp + s4_gp
        lp_moic = total_lp / wf_inv if wf_inv > 0 else 0
        eff_carry = total_gp / profit * 100 if profit > 0 else 0

        _header(s, "WATERFALL DISTRIBUTION", "Waterfall 분배 시뮬레이션",
                f'LP에게 {total_lp:,.0f}M(MOIC {lp_moic:.2f}x), GP에게 {total_gp:,.0f}M이 분배되며 실효 Carry는 {eff_carry:.1f}%입니다.')

        # 좌측: 파라미터 + 차트
        _shape(s, M_LEFT, BODY_Y, Inches(6.3), Inches(0.35), C_XPALE, C_PALE, radius=True)
        _txt(s, M_LEFT + Inches(0.1), BODY_Y + Inches(0.06), Inches(6.1), Inches(0.2),
             f"투자금 {wf_inv:,.0f}M · 회수금 {wf_proc:,.0f}M · Hurdle {hurdle}% · Carry {carry}% · {years}년",
             sz=9, color=C_PRIMARY, bold=True, align=PP_ALIGN.CENTER)

        if include_charts:
            import plotly.graph_objects as go
            labels = ["① 원금반환", "② 우선수익", "③ GP Catch-up", "④ Carry Split"]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="LP", x=labels, y=[s1, s2, 0, s4_lp],
                                 marker_color="#1b5e20",
                                 text=[f"{v:,.0f}" for v in [s1, s2, 0, s4_lp]],
                                 textposition="inside", textfont=dict(color="#fff", size=9)))
            fig.add_trace(go.Bar(name="GP", x=labels, y=[0, 0, s3_gp, s4_gp],
                                 marker_color="#a5d6a7",
                                 text=[f"{v:,.0f}" if v > 0 else "" for v in [0, 0, s3_gp, s4_gp]],
                                 textposition="inside", textfont=dict(size=9)))
            fig.update_layout(barmode="stack", height=250, width=550, margin=dict(t=10, b=30, l=40, r=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              legend=dict(orientation="h", y=-0.18), bargap=0.3,
                              yaxis=dict(showgrid=True, gridcolor="#eee", title="백만원"))
            _chart_img(s, fig, 0.6, 2.0, 6.0, 3.0)

        # 우측: 분배 상세 테이블
        wf_hdrs = ["단계", "LP", "GP", "설명"]
        wf_cw = [Inches(1.2), Inches(1.0), Inches(1.0), Inches(2.0)]
        wf_rows = [
            ["① 원금반환", f"{s1:,.0f}", "-", "LP 투자 원금 반환"],
            ["② 우선수익", f"{s2:,.0f}", "-", f"Hurdle {hurdle}% × {years}년"],
            ["③ GP Catch-up", "-", f"{s3_gp:,.0f}", f"GP Carry 목표 보전"],
            ["④ Carry Split", f"{s4_lp:,.0f}", f"{s4_gp:,.0f}", f"LP {100-carry}% / GP {carry}%"],
            ["합계", f"{total_lp:,.0f}", f"{total_gp:,.0f}", f"총 {wf_proc:,.0f}M"],
        ]
        _table(s, Inches(7.0), BODY_Y + Inches(0.50), wf_hdrs, wf_rows, wf_cw, Inches(0.30))

        # 테이블 아래: 분배 구조 설명
        wf_desc_y = BODY_Y + Inches(0.50) + Inches(0.30 * 6) + Inches(0.10)
        wf_descs = [
            "① 원금반환: LP가 투자한 원금을 최우선으로 반환받는 단계",
            f"② 우선수익: LP에게 Hurdle Rate({hurdle}%) 기준 {years}년간 우선수익을 배분",
            "③ GP Catch-up: GP가 전체 수익의 Carry 비율만큼 추가 수취",
            f"④ Carry Split: 잔여 수익을 LP({100-carry}%)와 GP({carry}%)가 분배",
        ]
        _multiline(s, Inches(7.0), wf_desc_y, Inches(5.2), Inches(1.0), wf_descs, sz=8, color=C_DARK, spacing=4)

        # 하단 KPI — 3개 + 인사이트
        ky = Inches(5.5)
        kw = Inches(2.9)
        _kpi_card(s, M_LEFT, ky, kw, Inches(0.70), "LP 수취", f"{total_lp:,.0f}M", f"MOIC {lp_moic:.2f}x", C_PRIMARY)
        _kpi_card(s, M_LEFT + Inches(3.05), ky, kw, Inches(0.70), "GP Carry", f"{total_gp:,.0f}M", f"실효 {eff_carry:.1f}%", C_ACCENT)
        _kpi_card(s, M_LEFT + Inches(6.10), ky, kw, Inches(0.70), "수익 배분", f"{total_lp/wf_proc*100:.0f}% / {total_gp/wf_proc*100:.0f}%" if wf_proc > 0 else "-", "LP / GP", C_BLACK)

        wf_ins = [
            f"LP는 총 {total_lp:,.0f}M을 수취하여 MOIC {lp_moic:.2f}x를 달성하였습니다.",
            f"{'LP 원금 이상 회수 완료' if lp_moic >= 1.0 else 'LP 원금 미달 — Hurdle 수익률 확보를 위한 추가 회수 필요'}",
        ]
        _insight_panel(s, M_LEFT + Inches(9.15), ky, Inches(3.5), Inches(0.85), "DISTRIBUTION", wf_ins)
        slide_labels.append("Waterfall")

    # ════════════════════════════════════════════════
    # 12. KVIC 시장 비교
    # ════════════════════════════════════════════════
    if _sec("KVIC") and kvic_sector_df is not None and not kvic_sector_df.empty:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        kvic_total = kvic_sector_df["총약정액(억원)"].sum()
        kvic_funds = int(kvic_sector_df["조합수"].sum())
        my_inv = result_df["투자금액_백만원"].sum() / 100
        avg_fund = kvic_total / kvic_funds if kvic_funds > 0 else 0

        _header(s, "KVIC MARKET COMPARISON", "KVIC 시장 비교",
                f'내 펀드 규모 {my_inv:,.0f}억원은 KVIC 전체 {kvic_total:,.0f}억원({kvic_funds:,}개 조합) 대비 평균 조합의 {my_inv/avg_fund:.1f}배 수준입니다.' if avg_fund > 0 else f'KVIC 전체 {kvic_total:,.0f}억원 시장과 내 펀드를 비교 분석합니다.')

        # KPI 행
        _kpi_card(s, M_LEFT, BODY_Y, Inches(2.85), Inches(0.90), "내 펀드 규모", f"{my_inv:,.0f}억",
                  f"KVIC의 {my_inv/kvic_total*100:.3f}%" if kvic_total > 0 else "", C_PRIMARY)
        _kpi_card(s, M_LEFT + Inches(3.05), BODY_Y, Inches(2.85), Inches(0.90), "KVIC 전체", f"{kvic_total:,.0f}억",
                  f"{kvic_funds:,}개 조합", C_ACCENT)
        _kpi_card(s, M_LEFT + Inches(6.10), BODY_Y, Inches(2.85), Inches(0.90), "평균 조합 대비",
                  f"{my_inv/avg_fund:.1f}배" if avg_fund > 0 else "-",
                  f"평균 {avg_fund:,.0f}억/조합", C_PRIMARY)
        _kpi_card(s, M_LEFT + Inches(9.15), BODY_Y, Inches(2.85), Inches(0.90), "투자 분야",
                  f"{len(kvic_sector_df)}개", "KVIC 섹터 수", C_BLACK)

        # 좌측: 차트
        if include_charts:
            import plotly.graph_objects as go
            top8 = kvic_sector_df.head(8)
            fig = go.Figure(go.Bar(
                x=top8["총약정액(억원)"].tolist(), y=top8["투자분야"].tolist(), orientation="h",
                marker_color="rgba(27,94,32,0.6)", marker_line_width=0,
                text=[f"{v:,.0f}억" for v in top8["총약정액(억원)"]], textposition="outside", textfont=dict(size=8),
            ))
            fig.update_layout(height=220, width=550, margin=dict(t=5, b=10, l=100, r=40),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              yaxis=dict(autorange="reversed", showgrid=False),
                              xaxis=dict(showgrid=True, gridcolor="#eee"), bargap=0.25)
            _chart_img(s, fig, 0.6, 2.55, 6.0, 2.8)

        # 우측: 섹터 테이블
        kv_hdrs = ["투자분야", "약정액(억)", "조합수", "비중(%)"]
        kv_cw = [Inches(1.5), Inches(0.9), Inches(0.7), Inches(0.7)]
        kv_rows = []
        for _, r in kvic_sector_df.head(8).iterrows():
            pct = r["총약정액(억원)"] / kvic_total * 100 if kvic_total > 0 else 0
            kv_rows.append([r["투자분야"], f'{r["총약정액(억원)"]:,.0f}', f'{int(r["조합수"])}', f'{pct:.1f}%'])
        _table(s, Inches(7.0), Inches(2.55), kv_hdrs, kv_rows, kv_cw, Inches(0.26))

        # 하단: 분석 과정 + 인사이트
        kv_bot = Inches(5.3)
        top_sector = kvic_sector_df.iloc[0]
        _txt(s, M_LEFT, kv_bot, Inches(3), Inches(0.18), "MARKET ANALYSIS", sz=9, color=C_GREY, bold=True)
        kv_process = [
            f"① KVIC 공시 데이터 기준 {kvic_funds:,}개 조합, 총 {kvic_total:,.0f}억원 시장 규모 확인",
            f"② 내 펀드 {my_inv:,.0f}억원은 KVIC 평균 조합({avg_fund:,.0f}억) 대비 {my_inv/avg_fund:.1f}배" if avg_fund > 0 else "② KVIC 평균 조합 대비 비교",
            f"③ KVIC 최대 분야: {top_sector['투자분야']} ({top_sector['총약정액(억원)']:,.0f}억, {top_sector['총약정액(억원)']/kvic_total*100:.0f}%)",
        ]
        _multiline(s, M_LEFT, kv_bot + Inches(0.20), Inches(5.8), Inches(0.9), kv_process, sz=9, color=C_DARK, spacing=5)

        kv_ins = [
            f"내 펀드는 KVIC 전체 시장의 {my_inv/kvic_total*100:.3f}%에 해당하며, 평균 조합 대비 {my_inv/avg_fund:.1f}배 규모입니다." if avg_fund > 0 else "",
            f"KVIC 시장 트렌드와 비교하여 포트폴리오 전략의 시장 적합성을 점검할 수 있습니다.",
        ]
        _insight_panel(s, Inches(6.5), kv_bot, Inches(6.2), Inches(1.0), "MARKET POSITIONING", [i for i in kv_ins if i])
        slide_labels.append("KVIC")

    # ════════════════════════════════════════════════
    # 13. 거시지표 · DART
    # ════════════════════════════════════════════════
    if _sec("거시") and (rate_df is not None or fx_df is not None):
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "MACRO & DART", "거시지표 · DART 재무", "현재 금리 및 환율 환경을 분석하고, 포트폴리오 기업의 DART 재무제표를 점검합니다.")

        # 거시 KPI
        col_i = 0
        kw = Inches(2.85)
        if rate_df is not None and not rate_df.empty:
            latest_rate = rate_df["기준금리(%)"].iloc[-1]
            rate_chg = round(rate_df["기준금리(%)"].iloc[-1] - rate_df["기준금리(%)"].iloc[0], 2) if len(rate_df) > 1 else 0
            _kpi_card(s, M_LEFT + Inches(col_i * 3.05), BODY_Y, kw, Inches(0.90),
                      "기준금리", f"{latest_rate}%", f"변동 {rate_chg:+.2f}%p", C_PRIMARY)
            col_i += 1
        if fx_df is not None and not fx_df.empty:
            latest_fx = fx_df["원/달러(원)"].iloc[-1]
            fx_chg = round(fx_df["원/달러(원)"].iloc[-1] - fx_df["원/달러(원)"].iloc[0]) if len(fx_df) > 1 else 0
            _kpi_card(s, M_LEFT + Inches(col_i * 3.05), BODY_Y, kw, Inches(0.90),
                      "원/달러", f"{latest_fx:,.0f}원", f"변동 {fx_chg:+.0f}원", C_BLACK)
            col_i += 1
        if spread is not None:
            _kpi_card(s, M_LEFT + Inches(col_i * 3.05), BODY_Y, kw, Inches(0.90),
                      "IRR vs 금리", f"{spread:+.1f}%p", "펀드 스프레드",
                      C_PRIMARY if spread > 0 else C_RED)
            col_i += 1

        # DART 재무 (있으면)
        if dart_fin_df is not None and not dart_fin_df.empty:
            dart_y = BODY_Y + Inches(1.15)
            _txt(s, M_LEFT, dart_y, Inches(5), Inches(0.2),
                 f"DART 재무제표 — {dart_company}", sz=11, color=C_BLACK, bold=True)

            # 차트
            if include_charts:
                import plotly.graph_objects as go
                cdf = dart_fin_df.copy()
                for col in ["매출액", "영업이익", "당기순이익"]:
                    if col in cdf.columns:
                        cdf[col] = cdf[col].apply(lambda x: round(x / 1e6) if pd.notna(x) else 0)
                fig = go.Figure()
                for col, clr in [("매출액", "#1b5e20"), ("영업이익", "#43a047"), ("당기순이익", "#a5d6a7")]:
                    if col in cdf.columns:
                        fig.add_trace(go.Bar(name=col, x=cdf["연도"].tolist(), y=cdf[col].tolist(),
                                             marker_color=clr, marker_line_width=0))
                fig.update_layout(barmode="group", height=220, width=500, margin=dict(t=5, b=25, l=40, r=10),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=0.3,
                                  legend=dict(orientation="h", y=-0.15), yaxis=dict(showgrid=True, gridcolor="#eee", title="백만원"))
                _chart_img(s, fig, 0.6, float(dart_y / 914400) + 0.30, 5.5, 2.8)

            # 우측: DART 테이블
            d_hdrs = ["연도", "매출액(M)", "영업이익(M)", "순이익(M)"]
            d_cw = [Inches(0.8), Inches(1.2), Inches(1.2), Inches(1.2)]
            d_rows = []
            for _, r in dart_fin_df.iterrows():
                yr = str(int(r["연도"])) if pd.notna(r.get("연도")) else ""
                rev = f"{r['매출액']/1e6:,.0f}" if pd.notna(r.get("매출액")) and r["매출액"] != 0 else "-"
                op = f"{r['영업이익']/1e6:,.0f}" if pd.notna(r.get("영업이익")) and r["영업이익"] != 0 else "-"
                ni = f"{r['당기순이익']/1e6:,.0f}" if pd.notna(r.get("당기순이익")) and r["당기순이익"] != 0 else "-"
                d_rows.append([yr, rev, op, ni])
            _table(s, Inches(6.8), BODY_Y + Inches(1.45), d_hdrs, d_rows, d_cw, Inches(0.28))

            # DART 재무 해석 (매출 성장률)
            try:
                valid = dart_fin_df[dart_fin_df["매출액"] > 0].sort_values("연도")
                if len(valid) >= 2:
                    rev_growth = (valid.iloc[-1]["매출액"] / valid.iloc[0]["매출액"]) ** (1 / max(len(valid) - 1, 1)) - 1
                    op_margin = valid.iloc[-1]["영업이익"] / valid.iloc[-1]["매출액"] * 100 if valid.iloc[-1]["매출액"] != 0 else 0
                    dart_note = f"{dart_company}: 연평균 매출 성장률 {rev_growth*100:.1f}%, 최근 영업이익률 {op_margin:.1f}%"
                else:
                    dart_note = f"{dart_company}: 재무 데이터 분석 중 — 추가 연도 데이터 확보 필요"
            except Exception:
                dart_note = ""
            if dart_note:
                _txt(s, Inches(6.8), BODY_Y + Inches(1.45) + Inches(0.28 * (len(d_rows) + 1)) + Inches(0.10),
                     Inches(5.2), Inches(0.4), dart_note, sz=8, color=C_GREY)

        # 하단: 거시경제 해석
        macro_bot = Inches(5.3)
        macro_texts = []
        if rate_df is not None and not rate_df.empty:
            macro_texts.append(f"기준금리 {latest_rate}%: {'인하 기조로 PE/VC 투자환경 개선 기대' if rate_chg < 0 else '금리 인상기로 밸류에이션 부담 증가 가능'}" if 'latest_rate' in dir() else "")
        if fx_df is not None and not fx_df.empty:
            macro_texts.append(f"환율 {latest_fx:,.0f}원: {'원화 약세로 해외 투자 포트폴리오 환차익 가능성' if fx_chg > 0 else '원화 강세로 해외 자산 환산 시 불리'}" if 'latest_fx' in dir() else "")
        if spread is not None:
            macro_texts.append(f"펀드 스프레드 {spread:+.1f}%p: {'금리 대비 초과수익 확보' if spread > 0 else '금리 수준에 미달하는 수익률'}")
        macro_texts = [t for t in macro_texts if t]
        if macro_texts:
            _txt(s, M_LEFT, macro_bot, Inches(3), Inches(0.18), "MACRO IMPACT", sz=9, color=C_GREY, bold=True)
            _multiline(s, M_LEFT, macro_bot + Inches(0.20), C_WIDTH, Inches(1.0), macro_texts, sz=9, color=C_DARK, spacing=5)
        slide_labels.append("거시지표")

    # ════════════════════════════════════════════════
    # 14. AI 코멘터리
    # ════════════════════════════════════════════════
    if _sec("AI") and commentary:
        s = prs.slides.add_slide(prs.slide_layouts[6]); _bg(s)
        _header(s, "AI COMMENTARY", "AI 분석 코멘터리 — Claude",
                "Claude AI가 전체 포트폴리오 데이터를 종합 분석하여 자동 생성한 분기 코멘터리입니다.")

        _shape(s, M_LEFT, BODY_Y, C_WIDTH, Inches(5.3), C_WHITE, C_PALE, radius=True)

        # AI 아이콘
        _shape(s, M_LEFT + Inches(0.15), BODY_Y + Inches(0.15), Inches(0.35), Inches(0.35), C_PRIMARY, radius=True)
        _txt(s, M_LEFT + Inches(0.15), BODY_Y + Inches(0.18), Inches(0.35), Inches(0.30),
             "AI", sz=9, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
        _txt(s, M_LEFT + Inches(0.60), BODY_Y + Inches(0.20), Inches(4), Inches(0.25),
             "Claude AI 분기 코멘터리", sz=11, color=C_PRIMARY, bold=True)

        # 본문 (최대 20줄)
        lines = [l for l in commentary.split("\n") if l.strip()][:20]
        _multiline(s, M_LEFT + Inches(0.20), BODY_Y + Inches(0.55), C_WIDTH - Inches(0.40),
                   Inches(4.8), lines, sz=10, color=C_DARK, spacing=4)
        slide_labels.append("AI")

    # ════════════════════════════════════════════════
    # 마지막: End of Document
    # ════════════════════════════════════════════════
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(s, C_PRIMARY)
    _txt(s, Inches(0), Inches(2.8), SW, Inches(0.9),
         "End of Document", sz=48, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
    _shape(s, Inches(1.5), Inches(3.8), Inches(10.333), Pt(2), C_LIGHT)
    _txt(s, Inches(0), Inches(4.1), SW, Inches(0.4),
         "이수빈", sz=16, color=C_LIGHT, align=PP_ALIGN.CENTER)
    _txt(s, Inches(0), Inches(4.6), SW, Inches(0.3),
         f"{fund_name}  ·  {quarter}  ·  PE/VC 분기 보고 도우미", sz=10, color=C_PALE, align=PP_ALIGN.CENTER)
    _txt(s, Inches(0), Inches(6.2), SW, Inches(0.3),
         "본 보고서는 자동 생성된 참고 자료이며, 투자 의사결정의 최종 근거로 사용할 수 없습니다.", sz=8, color=C_LIGHT, align=PP_ALIGN.CENTER)
    slide_labels.append("End")

    # ── 페이지 번호 ─────────────────────────────────
    total = len(prs.slides)
    for i, slide in enumerate(prs.slides):
        if 0 < i < total - 1:
            _page_num(slide, i + 1, total)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
