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
            pdf.add_font(name, "", path, uni=True)
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
