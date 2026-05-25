import pandas as pd
from fpdf import FPDF


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

    # 한글 폰트 시도, 없으면 Helvetica fallback
    try:
        pdf.add_font("NanumGothic", "", "NanumGothic.ttf", uni=True)
        font = "NanumGothic"
    except Exception:
        font = "Helvetica"

    # ── 제목
    pdf.set_font(font, size=18)
    title = f"PE/VC Portfolio Report"
    if quarter:
        title += f"  {quarter}"
    pdf.cell(0, 14, title, ln=True, align="C")
    pdf.ln(4)

    # ── 펀드 요약
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, "1. Fund Summary", ln=True)
    pdf.set_font(font, size=10)
    skip = {"포트폴리오사 수"}
    for k, v in summary.items():
        if k not in skip:
            pdf.cell(0, 7, f"   {k}: {v}", ln=True)
    pdf.ln(4)

    # ── 포트폴리오 테이블
    pdf.set_font(font, size=13)
    pdf.cell(0, 9, "2. Portfolio Companies", ln=True)
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
    pdf.cell(0, 9, "3. Commentary", ln=True)
    pdf.set_font(font, size=10)
    pdf.multi_cell(0, 6, commentary)

    return bytes(pdf.output())
