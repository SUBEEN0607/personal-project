import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
import base64, os, re, requests

from calculator import load_portfolio, run_all, portfolio_summary
from rag import answer_question
from irr import j_curve_data
from simulator import simulate_exit, optimal_exit_timing
from db import save_snapshot, load_quarters, load_trend
from report import (
    generate_pdf,
    generate_full_pdf,
    generate_jcurve_pdf,
    generate_scenario_pdf,
    generate_quarterly_pdf,
    generate_dart_pdf,
    generate_macro_pdf,
)
from dart_client import search_company, get_financials
from benchmark import (
    get_base_rate, get_exchange_rate, get_vc_trend,
    get_kvic_sector_summary, get_kvic_yearly_trend,
)
from commentary import (
    generate_commentary,
    interpret_jcurve,
    interpret_scenario,
    interpret_quarterly_trend,
    interpret_dart_financials,
    interpret_macro,
)

# valuation_fetcher는 버튼 클릭 시 지연 import (BeautifulSoup 로딩 지연)

st.set_page_config(page_title="PE/VC 분기 보고 도우미", layout="wide")

# ── 표지/앱 전환 상태 ─────────────────────────────
if "show_cover" not in st.session_state:
    st.session_state["show_cover"] = True

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

/* ── Design System ── */
html, body, [class*="css"], .stApp {
    font-family: 'Pretendard', -apple-system, system-ui, sans-serif !important;
    background-color: #ffffff !important;
    color: #1a1a1a !important;
}
[data-testid="stAppViewContainer"] { background-color: #ffffff !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e5e5e5 !important;
    border-left: none !important;
}

/* Typography — tight, bold headings */
h1 { font-size: 32px !important; font-weight: 800 !important; letter-spacing: -0.04em !important; }
h2 { font-size: 22px !important; font-weight: 700 !important; letter-spacing: -0.03em !important; }
h3 { font-size: 18px !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
h4 { font-size: 15px !important; font-weight: 600 !important; letter-spacing: -0.01em !important; }
h1,h2,h3,h4,h5,h6 { color: #1a1a1a !important; }

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e5e5e5 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    background: #ffffff !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: none !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: none;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important; color: #999 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-size: 30px !important; font-weight: 800 !important;
    color: #1a1a1a !important; letter-spacing: -0.04em !important;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 500 !important; }

/* Tabs — minimal underline */
[data-baseweb="tab-list"] { border-bottom: 1px solid #eae8e4 !important; gap: 0 !important; }
[data-baseweb="tab"] {
    font-size: 13px !important; font-weight: 500 !important;
    color: #999 !important; padding: 12px 20px !important;
    border-radius: 0 !important; letter-spacing: 0.01em !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1a1a1a !important;
    border-bottom: 2px solid #1b5e20 !important;
    background-color: transparent !important;
    font-weight: 600 !important;
}

/* Buttons — clean, subtle */
.stButton > button {
    color: #1a1a1a !important;
    border: 1px solid #ddd !important;
    background-color: #ffffff !important;
    border-radius: 8px !important;
    padding: 8px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    border-color: #1b5e20 !important;
    color: #1b5e20 !important;
    background-color: #f5f9f5 !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background-color: #e8dcc8 !important;
    color: #1a1a1a !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 10px 36px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background-color: #d4c4a8 !important;
    color: #1a1a1a !important;
}

/* Download button — accent */
.stDownloadButton > button {
    background-color: #1b5e20 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    background-color: #14471a !important;
    color: #ffffff !important;
}

/* DataFrames — green header */
[data-testid="stDataFrame"] thead th, [data-testid="stDataFrame"] th {
    background-color: #1b5e20 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 11px !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    text-align: center !important;
    padding: 10px 14px !important;
    border: none !important;
}
[data-testid="stDataFrame"] tbody td {
    text-align: center !important;
    padding: 10px 14px !important;
    border-bottom: 1px solid #eee !important;
    font-size: 13px !important;
    background-color: #ffffff !important;
}
[data-testid="stDataFrame"] tbody tr:hover td { background-color: #f0f7f0 !important; }

/* Inputs — subtle */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    border: 1px solid #ddd !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    background-color: #ffffff !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #1b5e20 !important;
    box-shadow: 0 0 0 2px rgba(27,94,32,0.08) !important;
}
[data-baseweb="input"]:focus-within {
    border-color: #1b5e20 !important;
    box-shadow: 0 0 0 2px rgba(27,94,32,0.08) !important;
}

/* Selectbox, Slider */
[data-testid="stSelectbox"] > div > div { border: 1px solid #ddd !important; border-radius: 8px !important; }
[data-testid="stSlider"] [role="slider"] { color: #1b5e20 !important; }

/* Expander */
[data-testid="stExpander"] { border: 1px solid #e5e5e5 !important; border-radius: 12px !important; background: #ffffff !important; }

/* Divider */
hr { border: none !important; border-top: 1px solid #ddd !important; margin: 20px 0 !important; }

/* Alert */
.stAlert > div { border-radius: 10px !important; }

/* Hide clutter */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Cover button */
.cover-btn > button {
    background-color: transparent !important;
    color: #ffffff !important;
    border: 1.5px solid rgba(255,255,255,0.5) !important;
    border-radius: 24px !important;
    padding: 12px 36px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
}
.cover-btn > button:hover {
    background-color: rgba(255,255,255,0.12) !important;
    border-color: #ffffff !important;
    color: #ffffff !important;
}

/* Custom card class */
.clean-card {
    background: #ffffff;
    border: 1px solid #eae8e4;
    border-radius: 10px;
    padding: 24px;
}
.stat-large {
    font-size: 48px;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1;
    color: #1a1a1a;
}
.stat-label {
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #999;
    font-weight: 500;
    margin-bottom: 6px;
}
.stat-desc {
    font-size: 12px;
    color: #999;
    margin-top: 8px;
}
.accent { color: #1b5e20; }
.section-label {
    font-size: 10px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #bbb;
    font-weight: 600;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── 배경 이미지 base64 로드 ───────────────────────
_wp_b64 = ""
for _try_path in [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "skku_wallpaper.jpg"),
    os.path.join(os.getcwd(), "skku_wallpaper.jpg"),
    r"C:\Users\Lenovo\personal-project\skku_wallpaper.jpg",
]:
    if os.path.exists(_try_path):
        with open(_try_path, "rb") as _f:
            _wp_b64 = base64.b64encode(_f.read()).decode()
        break

if st.session_state["show_cover"]:
    _b64_src = f"data:image/jpeg;base64,{_wp_b64}" if _wp_b64 else ""

    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{ background: transparent !important; }}
    [data-testid="stMain"] {{ background: transparent !important; }}
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 0 !important; max-width: 100% !important; }}
    section[data-testid="stMain"] > div {{ padding: 0 !important; }}
    .stMainBlockContainer {{ max-width: 100% !important; padding: 0 !important; }}
    html, body, .stApp {{ background: transparent !important; }}
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    section[data-testid="stMain"] > div {{ padding: 0 !important; }}
    .block-container {{ padding: 0 !important; max-width: 100% !important; }}

    .cv-full {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        overflow: hidden; z-index: 0; pointer-events: none;
    }}
    .cv-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: {"url('" + _b64_src + "') center/cover no-repeat" if _b64_src else "linear-gradient(135deg,#2d7a35,#1b5e20)"};
    }}
    .cv-overlay {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(180deg,
            rgba(15,50,20,0.3) 0%,
            rgba(20,60,25,0.45) 40%,
            rgba(15,45,18,0.6) 65%,
            rgba(10,30,12,0.8) 100%);
    }}
    .cv-content {{
        position: relative; width: 100%; min-height: 100vh;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        text-align: center; z-index: 10; padding: 40px 20px;
    }}
    .cv-top {{ font-size:12px; color:rgba(255,255,255,0.7); letter-spacing:0.3em;
        text-transform:uppercase; margin-bottom:40px; font-weight:600;
        text-shadow:0 2px 10px rgba(0,0,0,0.5); }}
    .cv-title {{ font-size:clamp(80px,12vw,150px); font-weight:900; line-height:0.88;
        letter-spacing:-0.04em; color:#fff;
        text-shadow:0 0 80px rgba(255,255,255,0.15), 0 6px 30px rgba(0,0,0,0.5); }}
    .cv-sub {{ font-size:clamp(24px,3.5vw,42px); font-weight:700; letter-spacing:0.08em;
        margin-top:10px; color:rgba(255,255,255,0.9);
        text-shadow:0 4px 15px rgba(0,0,0,0.5); }}
    .cv-tags {{ display:flex; gap:10px; flex-wrap:wrap; justify-content:center;
        margin-top:50px; margin-bottom:25px; }}
    .cv-tag {{ font-size:10px; color:rgba(255,255,255,0.55); letter-spacing:0.06em;
        padding:4px 14px; border:1px solid rgba(255,255,255,0.2); border-radius:20px; }}
    .cv-name {{ font-size:12px; color:rgba(255,255,255,0.55); letter-spacing:0.08em;
        font-weight:500; text-shadow:0 2px 8px rgba(0,0,0,0.4); }}
    .cv-enter {{ margin-top:30px; }}
    .cv-enter button {{
        background: transparent !important; color: #fff !important;
        border: 1.5px solid rgba(255,255,255,0.4) !important;
        border-radius: 24px !important; padding: 10px 40px !important;
        font-size: 13px !important; letter-spacing: 0.05em !important;
        cursor: pointer !important;
    }}
    .cv-enter button:hover {{
        background: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.6) !important;
    }}
    </style>

    <div class="cv-full">
        <div class="cv-bg"></div>
        <div class="cv-overlay"></div>
        <div class="cv-content">
            <div class="cv-top">SDIC &middot; SKKU Digital IT Consulting</div>
            <div class="cv-title">PE/VC</div>
            <div class="cv-sub">분기 보고 도우미</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:16px;margin-bottom:32px;line-height:1.6;max-width:520px;">
                데이터 수집부터 성과 분석, LP 보고서와 IC 장표 작성까지<br>분기 보고에 필요한 모든 과정을 하나의 화면에서 완성합니다.
            </div>
            <div class="cv-tags">
                <span class="cv-tag">DART</span>
                <span class="cv-tag">ECOS</span>
                <span class="cv-tag">KVIC</span>
                <span class="cv-tag">Claude AI</span>
            </div>
            <div class="cv-name">이수빈 &middot; 개인 프로젝트</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:500px; position:relative; z-index:100; text-align:center; padding-bottom:50px;">',
        unsafe_allow_html=True,
    )
    col_l, col_c, col_r = st.columns([2, 1, 2])
    with col_c:
        if st.button("Enter →", use_container_width=True, type="primary"):
            st.session_state["show_cover"] = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# ── 일반 헤더: 표지 통과 후 ──────────────────────
st.markdown("""
<div style="padding: 0 0 20px 0; border-bottom: 1px solid #e5e5e5; margin-bottom: 24px;">
  <div style="display:flex; align-items:baseline; gap:12px;">
    <span style="font-size:24px; font-weight:800; color:#1a1a1a; letter-spacing:-0.04em;">PE/VC</span>
    <span style="font-size:13px; font-weight:400; color:#bbb;">분기 보고 도우미</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding: 12px 0 16px 0; border-bottom: 1px solid #eae8e4; margin-bottom: 20px;">
  <div style="font-size: 20px; font-weight: 800; color: #1a1a1a; letter-spacing:-0.04em;">PE/VC</div>
  <div style="font-size: 10px; color: #bbb; letter-spacing: 0.1em; font-weight: 500; margin-top: 2px;">SDIC · 이수빈</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">펀드 정보</p>', unsafe_allow_html=True)
    fund_name = st.text_input("펀드명", value="SDIC 성장투자 1호")
    fund_strategy = st.selectbox("전략", ["벤처캐피탈(VC)", "성장투자(Growth)", "바이아웃(Buyout)", "혼합(Hybrid)"])

    st.markdown("---")
    st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">데이터</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader("CSV / Excel", type=["csv", "xlsx"])
    use_sample = st.button("샘플 데이터 불러오기")

    st.markdown("---")
    st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">템플릿</p>', unsafe_allow_html=True)
    if st.button("Excel 입력 가이드 다운로드", use_container_width=True):
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        guide_buf = io.BytesIO()
        with pd.ExcelWriter(guide_buf, engine="openpyxl") as w:
            # ── 시트1: 샘플 데이터 (5개사) ──
            sample = pd.DataFrame({
                "회사명": ["넥스틸바이오", "코리아로지텍", "그린솔라원", "미래모빌리티", "케어에이아이"],
                "섹터": ["바이오", "SaaS/물류", "신재생에너지", "모빌리티", "의료AI"],
                "투자단계": ["Series B", "Series A", "Pre-A", "Series C", "Series B"],
                "투자일": ["2020-04-10", "2021-02-20", "2020-08-15", "2021-11-01", "2020-06-30"],
                "기준일": ["2024-06-30", "2024-06-30", "2024-06-30", "2024-06-30", "2024-06-30"],
                "투자금액_백만원": [1500, 600, 300, 4000, 1200],
                "현재가치_백만원": [5100, 1560, 0, 3200, 3840],
                "회수금액_백만원": [0, 0, 960, 0, 0],
                "지분율_%": [8.5, 12.0, 15.0, 5.0, 10.0],
            })
            sample.to_excel(w, sheet_name="샘플데이터", index=False)

            # ── 시트2: 컬럼 가이드 ──
            guide = pd.DataFrame({
                "컬럼명": ["회사명","섹터","투자단계","투자일","기준일","투자금액_백만원","현재가치_백만원","회수금액_백만원","지분율_%"],
                "필수": ["필수","필수","필수","필수","필수","필수","선택","필수","선택"],
                "데이터 타입": ["텍스트","텍스트","텍스트","날짜","날짜","숫자","숫자","숫자","숫자"],
                "설명": [
                    "포트폴리오 회사명 (정확한 법인명 권장 — DART 검색에 사용)",
                    "투자 섹터 (바이오, SaaS, 모빌리티, 에듀테크, 핀테크, AI, 딥테크, 애그테크 등)",
                    "투자 라운드 단계 (Pre-A, Seed, Series A, Series B, Series C, Growth 등)",
                    "최초 투자 실행일 (YYYY-MM-DD 형식, 예: 2022-01-15)",
                    "현재가치 평가 기준일 (YYYY-MM-DD 형식, 보통 분기 말일)",
                    "투자 원금 (백만원 단위, 예: 1500 = 15억원)",
                    "현재 평가가치 (백만원). 0이면 자동 밸류에이션 조회 기능 사용 가능",
                    "이미 회수한 금액 (백만원). 배당, 일부 매각 등. 미회수 시 0",
                    "취득 지분율 (%). 자동 밸류에이션 시 시가총액 × 지분율로 계산. 미입력 시 10% 기본값",
                ],
                "예시값": ["넥스틸바이오","바이오","Series B","2020-04-10","2024-06-30","1500","5100","0","8.5"],
            })
            guide.to_excel(w, sheet_name="입력가이드", index=False)

            # ── 시트3: 섹터 목록 ──
            sectors = pd.DataFrame({
                "섹터명": ["바이오","의료AI","SaaS","SaaS/물류","모빌리티","자율주행","에듀테크",
                          "신재생에너지","딥테크","AI","반도체","핀테크","커머스","콘텐츠","게임",
                          "애그테크","푸드테크","물류","ESG","헬스케어"],
                "P/S 배수 (참고)": [8.0,7.0,5.0,4.5,3.0,5.0,3.5,2.5,5.0,7.0,6.0,4.5,2.0,3.0,4.0,3.0,2.5,2.0,2.0,4.0],
                "설명": [
                    "제약/바이오텍 (임상 단계에 따라 변동 큼)",
                    "의료 AI/디지털 헬스케어",
                    "B2B SaaS, 클라우드 서비스",
                    "물류 SaaS, 물류 플랫폼",
                    "전기차, 공유 모빌리티",
                    "자율주행 기술, 라이다/센서",
                    "에듀테크, 온라인 교육",
                    "태양광, 풍력, ESS",
                    "소재, 양자컴퓨팅 등 원천기술",
                    "생성형 AI, MLOps",
                    "팹리스, 시스템 반도체",
                    "간편결제, 로보어드바이저",
                    "이커머스, D2C",
                    "미디어, 웹툰, IP",
                    "모바일/PC 게임",
                    "스마트팜, 농업기술",
                    "대체식품, 배달",
                    "풀필먼트, 라스트마일",
                    "탄소배출, 그린테크",
                    "디지털 치료제, 원격의료",
                ],
            })
            sectors.to_excel(w, sheet_name="섹터목록", index=False)

            # ── 스타일 적용 ──
            wb = w.book
            green_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
            light_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
            white_font = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=11)
            body_font  = Font(name="맑은 고딕", size=10)
            thin_border = Border(
                left=Side(style="thin", color="C8E6C9"),
                right=Side(style="thin", color="C8E6C9"),
                top=Side(style="thin", color="C8E6C9"),
                bottom=Side(style="thin", color="C8E6C9"),
            )
            center = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                # 헤더 스타일
                for cell in ws[1]:
                    cell.fill = green_fill
                    cell.font = white_font
                    cell.alignment = center
                    cell.border = thin_border
                # 바디 스타일
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                    for i, cell in enumerate(row):
                        cell.font = body_font
                        cell.border = thin_border
                        cell.alignment = left_wrap if isinstance(cell.value, str) and len(str(cell.value)) > 15 else center
                    # 짝수 행 연한 초록
                    if cell.row % 2 == 0:
                        for c in row:
                            c.fill = light_fill
                # 컬럼 너비 자동
                for col in ws.columns:
                    max_len = 0
                    col_letter = col[0].column_letter
                    for cell in col:
                        val = str(cell.value) if cell.value else ""
                        # 한글은 2칸으로 계산
                        char_len = sum(2 if ord(c) > 127 else 1 for c in val)
                        max_len = max(max_len, char_len)
                    ws.column_dimensions[col_letter].width = min(max_len + 4, 50)
                # 행 높이
                ws.row_dimensions[1].height = 28
                for r in range(2, ws.max_row + 1):
                    ws.row_dimensions[r].height = 24 if sheet_name != "입력가이드" else 40

        st.download_button(
            "다운로드", guide_buf.getvalue(),
            file_name="PE_VC_입력_가이드.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">분기 저장</p>', unsafe_allow_html=True)
    quarter = st.text_input("분기 (예: 2024Q1)", value="2024Q1")
    if st.button("현재 데이터 저장"):
        if "result_df" in st.session_state:
            save_snapshot(st.session_state["result_df"], quarter)
            st.success(f"{quarter} 저장 완료")
        else:
            st.warning("먼저 데이터를 로드하세요.")

if uploaded:
    if uploaded.name.endswith(".xlsx"):
        xl = pd.ExcelFile(uploaded)
        sheet = st.sidebar.selectbox("시트 선택", xl.sheet_names)
        raw = pd.read_excel(uploaded, sheet_name=sheet)
    else:
        raw = pd.read_csv(uploaded)
    raw["투자일"] = pd.to_datetime(raw["투자일"])
    raw["기준일"] = pd.to_datetime(raw["기준일"])
    result_df = run_all(raw)
    st.session_state["df"] = raw
    st.session_state["result_df"] = result_df
    st.session_state["summary"] = portfolio_summary(raw)
    st.sidebar.success(f"{len(raw)}개사 로드 완료")

elif use_sample:
    raw = load_portfolio("sample_portfolio.csv")
    result_df = run_all(raw)
    st.session_state["df"] = raw
    st.session_state["result_df"] = result_df
    st.session_state["summary"] = portfolio_summary(raw)
    st.sidebar.success("샘플 데이터(8개사) 로드됨")

# ── 자동 밸류에이션 조회 ──────────────────────────
if "df" in st.session_state:
    with st.expander("Automated Valuation — 포트폴리오 현재가치 자동 추정"):
        st.markdown("""
<div style="background:#ffffff;border:1px solid #c8e6c9;border-radius:10px;padding:18px 22px;margin-bottom:16px;">
  <div style="font-size:14px;font-weight:700;color:#1b5e20;margin-bottom:10px;">밸류에이션 방법론</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:12px;color:#555;line-height:1.7;">
    <div>
      <div style="font-weight:600;color:#1a1a1a;margin-bottom:4px;">상장사 (Market Cap)</div>
      네이버 금융에서 실시간 시가총액을 크롤링한 후 입력된 지분율(%)을 곱하여 보유 지분 가치를 산출합니다.
      <div style="color:#999;font-size:11px;margin-top:4px;">시총 × 지분율 = 현재가치</div>
    </div>
    <div>
      <div style="font-weight:600;color:#1a1a1a;margin-bottom:4px;">비상장사 (Comparable Multiple)</div>
      DART에서 최근 재무제표를 조회하고, P/S · EV/EBITDA · P/E 3가지 멀티플의 가중평균으로 기업가치를 추정합니다.
      <div style="color:#999;font-size:11px;margin-top:4px;">매출×P/S + 영업이익×EV/EBITDA + 순이익×P/E → 평균 EV × 지분율</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#999;font-weight:700;margin-bottom:6px;">INPUT — 지분율 입력</p>', unsafe_allow_html=True)

        av_df = st.session_state["df"][["회사명", "섹터", "투자금액_백만원", "현재가치_백만원"]].copy()
        if "지분율_%" not in av_df.columns:
            av_df["지분율_%"] = 10.0
        else:
            av_df["지분율_%"] = st.session_state["df"]["지분율_%"]

        edited_av = st.data_editor(
            av_df[["회사명", "섹터", "투자금액_백만원", "지분율_%"]],
            column_config={
                "회사명": st.column_config.TextColumn("회사명", disabled=True),
                "섹터": st.column_config.TextColumn("섹터", disabled=True),
                "투자금액_백만원": st.column_config.NumberColumn("투자금액 (M)", disabled=True, format="%d"),
                "지분율_%": st.column_config.NumberColumn("지분율 (%)", min_value=0, max_value=100, step=0.1, help="취득 지분율. 시가총액 × 이 비율 = 현재가치"),
            },
            use_container_width=True, hide_index=True, key="av_editor",
        )

        st.caption("ThreadPoolExecutor(6)으로 최대 6개사를 동시 병렬 조회합니다. 조회 시간 약 5~15초.")

        if st.button("자동 조회 실행", key="auto_val_btn", type="primary"):
            with st.spinner("DART · 네이버 금융 병렬 조회 중..."):
                from valuation_fetcher import bulk_fetch_valuations
                val_result = bulk_fetch_valuations(edited_av)
            st.session_state["val_result"] = val_result

        if "val_result" in st.session_state:
            vr = st.session_state["val_result"]

            st.markdown("---")
            st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#999;font-weight:700;margin-bottom:6px;">RESULT — 밸류에이션 결과</p>', unsafe_allow_html=True)

            # 회사별 결과 카드
            for _, row in vr.iterrows():
                est = row.get("현재가치_백만원_추정")
                source = row.get("source", "")
                basis = row.get("근거", "")
                detail = row.get("method_detail")
                corp = row.get("회사명", "")
                sector = row.get("섹터", "")
                inv = row.get("투자금액_백만원", 0)

                # 색상 결정
                if est and est > 0:
                    if inv > 0 and est > inv:
                        border_color = "#c8e6c9"
                        val_color = "#1b5e20"
                        moic_est = round(est / inv, 2)
                    else:
                        border_color = "#ffcdd2"
                        val_color = "#c62828"
                        moic_est = round(est / inv, 2) if inv > 0 else 0
                else:
                    border_color = "#e5e5e5"
                    val_color = "#999"
                    moic_est = 0

                # 상세 정보 라인
                detail_lines = []
                if detail and isinstance(detail, dict):
                    if "매출액_억" in detail and detail["매출액_억"]:
                        detail_lines.append(f"매출 {detail['매출액_억']}억")
                    if "영업이익률" in detail and detail["영업이익률"] is not None:
                        detail_lines.append(f"영업이익률 {detail['영업이익률']}%")
                    if "매출성장률" in detail and detail["매출성장률"] is not None:
                        g = detail["매출성장률"]
                        g_color = "#1b5e20" if g > 0 else "#c62828"
                        detail_lines.append(f"성장률 {g:+.1f}%")
                    if "적용배수" in detail and detail["적용배수"]:
                        multiples = " / ".join(f"{k}={v:.0f}억" for k, v in detail["적용배수"].items())
                        detail_lines.append(multiples)
                    if "시가총액_억" in detail:
                        mc = detail["시가총액_억"]
                        if mc >= 10000:
                            detail_lines.append(f"시총 {mc/10000:.1f}조")
                        else:
                            detail_lines.append(f"시총 {mc:,.0f}억")

                detail_str = " · ".join(detail_lines) if detail_lines else ""

                est_display = f"{est:,.0f}M" if est and est > 0 else "조회 실패"
                moic_display = f"MOIC {moic_est}x" if moic_est > 0 else ""

                st.markdown(f"""
<div style="background:#ffffff;border:1px solid {border_color};border-radius:10px;padding:16px 20px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
    <div>
      <span style="font-size:15px;font-weight:700;color:#1a1a1a;">{corp}</span>
      <span style="font-size:11px;color:#999;margin-left:8px;">{sector}</span>
      <span style="font-size:10px;color:#ccc;margin-left:8px;background:#f5f5f5;padding:2px 8px;border-radius:10px;">{source}</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:22px;font-weight:800;color:{val_color};">{est_display}</span>
      <span style="font-size:11px;color:{val_color};margin-left:6px;">{moic_display}</span>
    </div>
  </div>
  <div style="font-size:11px;color:#888;margin-top:6px;line-height:1.6;">
    {basis}
  </div>
  {"<div style='font-size:10px;color:#aaa;margin-top:4px;'>" + detail_str + "</div>" if detail_str else ""}
</div>
""", unsafe_allow_html=True)

            # 요약
            success = vr[vr["현재가치_백만원_추정"].notna() & (vr["현재가치_백만원_추정"] > 0)]
            failed = len(vr) - len(success)
            if len(success) > 0:
                total_est = success["현재가치_백만원_추정"].sum()
                st.markdown(f"""
<div style="background:#e8f5e9;border-radius:10px;padding:14px 20px;margin-top:12px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-size:12px;color:#1b5e20;font-weight:600;">조회 성공 {len(success)}개사</span>
      {"<span style='font-size:11px;color:#c62828;margin-left:12px;'>실패 " + str(failed) + "개사</span>" if failed > 0 else ""}
    </div>
    <div>
      <span style="font-size:11px;color:#666;">추정 총 가치</span>
      <span style="font-size:18px;font-weight:800;color:#1b5e20;margin-left:8px;">{total_est:,.0f}M</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            st.markdown("")
            if st.button("이 값으로 분석 실행", key="apply_val", type="primary"):
                raw_updated = st.session_state["df"].copy()
                applied = 0
                for _, row in vr.iterrows():
                    est = row.get("현재가치_백만원_추정")
                    if est and est > 0:
                        mask = raw_updated["회사명"] == row["회사명"]
                        raw_updated.loc[mask, "현재가치_백만원"] = est
                        applied += 1
                result_df = run_all(raw_updated)
                st.session_state["df"] = raw_updated
                st.session_state["result_df"] = result_df
                st.session_state["summary"] = portfolio_summary(raw_updated)
                st.success(f"{applied}개사 밸류에이션 업데이트 완료")
                st.rerun()

# ── 탭 ───────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Portfolio", "Analysis", "Benchmark", "Report",
])

# ── TAB 1: Performance ────────────────────────────
with tab1:
    if "result_df" not in st.session_state:
        st.info("사이드바에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        df        = st.session_state["df"]
        summary   = st.session_state["summary"]
        _GREEN    = ["#1b5e20","#2e7d32","#388e3c","#43a047","#66bb6a","#81c784","#a5d6a7","#c8e6c9"]

        moic    = summary["펀드 MOIC"]
        tvpi    = summary["펀드 TVPI"]
        dpi     = summary["펀드 DPI"]
        rvpi    = summary["펀드 RVPI"]
        n       = summary["포트폴리오사 수"]
        avg_irr = round(result_df["IRR(%)"].mean(), 1)
        total_invested = df["투자금액_백만원"].sum()
        total_value    = df["현재가치_백만원"].sum() + df["회수금액_백만원"].sum()
        base_date      = pd.to_datetime(df["기준일"]).max().strftime("%Y-%m-%d")

        # ── 펀드 헤더 ───────────────────────────────
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:baseline;
            margin-bottom:28px; flex-wrap:wrap; gap:8px;">
  <div>
    <div style="font-size:28px; font-weight:800; letter-spacing:-0.04em; color:#1a1a1a;">{fund_name}</div>
    <div style="font-size:12px; color:#bbb; margin-top:2px; letter-spacing:0.02em;">{fund_strategy} &middot; {quarter} &middot; {base_date}</div>
  </div>
  <div style="display:flex; gap:20px;">
    <div style="text-align:right;">
      <div style="font-size:10px; color:#bbb; letter-spacing:0.1em; text-transform:uppercase;">Portfolio</div>
      <div style="font-size:14px; font-weight:600; color:#1a1a1a;">{n}개사</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:10px; color:#bbb; letter-spacing:0.1em; text-transform:uppercase;">Invested</div>
      <div style="font-size:14px; font-weight:600; color:#1a1a1a;">{total_invested:,.0f}M</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Hero Metrics — MOIC + IRR ───────────────
        st.markdown(f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
  <div style="background:#ffffff; border:1px solid #c8e6c9; border-radius:12px; padding:28px 28px 24px;
              box-shadow: 0 4px 20px rgba(27,94,32,0.08);">
    <div class="stat-label">MOIC</div>
    <div class="stat-large" style="color:#1b5e20;">{moic}<span style="font-size:24px; color:#66bb6a;">x</span></div>
    <div class="stat-desc">투자원금 대비 전체 가치 배수</div>
  </div>
  <div style="background:#ffffff; border:1px solid #c8e6c9; border-radius:12px; padding:28px 28px 24px;
              box-shadow: 0 4px 20px rgba(27,94,32,0.08);">
    <div class="stat-label">IRR</div>
    <div class="stat-large" style="color:#1b5e20;">{avg_irr}<span style="font-size:24px; color:#66bb6a;">%</span></div>
    <div class="stat-desc">시간가치 반영 연환산 수익률</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── 보조 Metrics — DPI · RVPI · TVPI ───────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("DPI", f"{dpi}x", help="현금 회수 배수")
        m2.metric("RVPI", f"{rvpi}x", help="잔존 가치 배수")
        m3.metric("TVPI", f"{tvpi}x", help="DPI + RVPI")
        m4.metric("Companies", f"{n}개")

        # ── PE / VC 전략별 KPI ───────────────────────
        st.markdown("---")
        _is_vc = fund_strategy in ["벤처캐피탈(VC)"]
        _is_pe = fund_strategy in ["바이아웃(Buyout)"]
        _is_growth = fund_strategy in ["성장투자(Growth)"]

        if _is_vc:
            st.markdown("#### VC KPI — Growth Metrics")
            st.caption("벤처캐피탈 전략 선택 시 표시되는 성장 중심 지표")
            vc_cols = ["회사명", "섹터", "투자단계", "투자금액_백만원", "현재가치_백만원", "MOIC", "IRR(%)"]
            vc_available = [c for c in vc_cols if c in result_df.columns]
            vc_df = result_df[vc_available].copy()
            # VC 관점: 성장률 기반 추정 (현재가치/투자금액 = 성장배수)
            vc_df["성장배수"] = (result_df["현재가치_백만원"] / result_df["투자금액_백만원"]).round(2)
            invest_days = (pd.to_datetime(df["기준일"]) - pd.to_datetime(df["투자일"])).dt.days
            vc_df["투자기간(월)"] = (invest_days / 30).astype(int).values
            vc_df["월평균성장률(%)"] = ((vc_df["성장배수"] ** (1 / (vc_df["투자기간(월)"].clip(lower=1) / 12)) - 1) * 100).round(1)

            kv1, kv2, kv3 = st.columns(3)
            kv1.metric("평균 성장배수", f"{vc_df['성장배수'].mean():.2f}x")
            kv2.metric("평균 투자기간", f"{vc_df['투자기간(월)'].mean():.0f}개월")
            kv3.metric("연환산 성장률", f"{vc_df['월평균성장률(%)'].mean():.1f}%")

            st.dataframe(
                vc_df[["회사명", "섹터", "투자단계", "성장배수", "투자기간(월)", "월평균성장률(%)", "MOIC"]],
                use_container_width=True, hide_index=True,
            )

        elif _is_pe:
            st.markdown("#### PE KPI — Value Metrics")
            st.caption("바이아웃 전략 선택 시 표시되는 밸류에이션 중심 지표")
            pe_df = result_df[["회사명", "섹터", "투자금액_백만원", "현재가치_백만원", "회수금액_백만원", "MOIC", "IRR(%)", "DPI"]].copy()
            pe_df["실현비율(%)"] = (result_df["회수금액_백만원"] / (result_df["현재가치_백만원"] + result_df["회수금액_백만원"]).clip(lower=1) * 100).round(1)
            pe_df["미실현가치"] = result_df["현재가치_백만원"].apply(lambda x: f"{int(x):,}")

            kp1, kp2, kp3 = st.columns(3)
            kp1.metric("평균 DPI", f"{dpi}x", help="현금 회수 배수")
            kp2.metric("평균 실현비율", f"{pe_df['실현비율(%)'].mean():.1f}%")
            kp3.metric("총 회수금액", f"{int(df['회수금액_백만원'].sum()):,}M")

            st.dataframe(
                pe_df[["회사명", "섹터", "MOIC", "IRR(%)", "DPI", "실현비율(%)", "미실현가치"]],
                use_container_width=True, hide_index=True,
            )

        else:
            st.markdown("#### Fund KPI")
            if _is_growth:
                st.caption("성장투자 전략 — Growth + Value 혼합 지표")
            else:
                st.caption("혼합 전략 — 공통 지표")

        # ── Performance Summary ──────────────────────
        st.markdown("---")
        st.markdown("#### Performance Summary")
        perf_data = {
            "지표": ["MOIC", "IRR", "DPI", "RVPI", "TVPI"],
            "값": [f"{moic}x", f"{avg_irr}%", f"{dpi}x", f"{rvpi}x", f"{tvpi}x"],
            "정의": [
                "투자원금 대비 전체 가치 배수",
                "현금흐름 시간가치 반영 연환산 수익률",
                "LP 출자금 대비 현금 회수 배수",
                "LP 출자금 대비 잔존 미실현 가치",
                "DPI + RVPI",
            ],
            "벤치마크": ["≥ 2.0x", "≥ 15%", "1.0x = 원금회수", "초기 높음", "≥ 2.0x"],
        }
        perf_df = pd.DataFrame(perf_data)
        st.dataframe(perf_df, use_container_width=True, hide_index=True, height=215)

        with st.expander("용어 해설"):
            st.markdown("""
| 지표 | 설명 |
|------|------|
| **MOIC** | 원금 대비 총 가치. 시간가치 미반영. 2x = 2배 |
| **IRR** | 투자·회수 타이밍 반영 연환산 수익률. 장기 보유 시 낮아짐 |
| **DPI** | 실제 현금 회수 배수. 1.0x 이상 = 원금 회수 완료 |
| **RVPI** | 미회수 평가가치 배수. 펀드 초기에 높음 |
| **TVPI** | DPI + RVPI. LP 관점 총 가치 배수 |
""")

        st.markdown("---")

        # ── Portfolio Detail ─────────────────────────
        st.markdown("#### Portfolio Detail")

        display_df = result_df[["회사명","섹터","투자단계","투자금액_백만원","MOIC","IRR(%)","DPI","RVPI","TVPI"]].copy()
        display_df = display_df.rename(columns={
            "투자금액_백만원": "투자금액(백만)",
            "IRR(%)": "IRR(%)",
        })
        display_df["투자금액(백만)"] = display_df["투자금액(백만)"].apply(lambda x: f"{int(x):,}")

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=320)

        st.markdown("---")

        # ── Top / Bottom Performers ──────────────────
        st.markdown("#### Top / Bottom Performers")
        sorted_by_moic = result_df.sort_values("MOIC", ascending=False)
        top3 = sorted_by_moic.head(3)
        bottom3 = sorted_by_moic.tail(3)

        t_col, b_col = st.columns(2)
        with t_col:
            st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#1b5e20;font-weight:700;">TOP PERFORMERS</p>', unsafe_allow_html=True)
            for _, r in top3.iterrows():
                irr_val = r["IRR(%)"]
                irr_color = "#1b5e20" if irr_val > 0 else "#c62828"
                st.markdown(f"""
<div style="background:#ffffff;border:1px solid #c8e6c9;border-radius:10px;padding:14px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-size:15px;font-weight:700;color:#1a1a1a;">{r["회사명"]}</span>
      <span style="font-size:11px;color:#999;margin-left:8px;">{r["섹터"]}</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:20px;font-weight:800;color:#1b5e20;">{r["MOIC"]}x</span>
      <span style="font-size:12px;color:{irr_color};margin-left:8px;">IRR {irr_val}%</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        with b_col:
            st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#c62828;font-weight:700;">UNDERPERFORMERS</p>', unsafe_allow_html=True)
            for _, r in bottom3.iterrows():
                irr_val = r["IRR(%)"]
                moic_color = "#c62828" if r["MOIC"] < 1.0 else "#999"
                irr_color = "#c62828" if irr_val < 0 else "#999"
                st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e5e5e5;border-radius:10px;padding:14px 18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-size:15px;font-weight:700;color:#1a1a1a;">{r["회사명"]}</span>
      <span style="font-size:11px;color:#999;margin-left:8px;">{r["섹터"]}</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:20px;font-weight:800;color:{moic_color};">{r["MOIC"]}x</span>
      <span style="font-size:12px;color:{irr_color};margin-left:8px;">IRR {irr_val}%</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")

        # ── 포트폴리오 집중도 (HHI) + 투자 경과 ────────
        st.markdown("#### Portfolio Analytics")

        an1, an2 = st.columns(2)
        with an1:
            st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#999;font-weight:700;">CONCENTRATION (HHI)</p>', unsafe_allow_html=True)
            weights = df["투자금액_백만원"] / df["투자금액_백만원"].sum()
            hhi = round((weights ** 2).sum() * 10000)
            hhi_label = "높음 (집중)" if hhi > 2500 else ("보통" if hhi > 1500 else "낮음 (분산)")
            hhi_color = "#c62828" if hhi > 2500 else ("#ff9800" if hhi > 1500 else "#1b5e20")
            st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e5e5e5;border-radius:10px;padding:20px 24px;">
  <div style="font-size:36px;font-weight:800;color:{hhi_color};">{hhi:,}</div>
  <div style="font-size:12px;color:#999;margin-top:4px;">HHI 지수 · {hhi_label}</div>
  <div style="margin-top:12px;background:#f0f0f0;border-radius:6px;height:8px;overflow:hidden;">
    <div style="width:{min(hhi/100, 100)}%;height:100%;background:{hhi_color};border-radius:6px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;">
    <span style="font-size:9px;color:#ccc;">0 (완전분산)</span>
    <span style="font-size:9px;color:#ccc;">10,000 (단일집중)</span>
  </div>
</div>
""", unsafe_allow_html=True)

        with an2:
            st.markdown('<p style="font-size:11px;letter-spacing:0.1em;color:#999;font-weight:700;">INVESTMENT TIMELINE</p>', unsafe_allow_html=True)
            avg_days = (pd.to_datetime(df["기준일"]) - pd.to_datetime(df["투자일"])).dt.days.mean()
            avg_months = int(avg_days / 30)
            avg_years = round(avg_days / 365.25, 1)
            realized_pct = round(df["회수금액_백만원"].sum() / (df["현재가치_백만원"].sum() + df["회수금액_백만원"].sum()) * 100, 1) if (df["현재가치_백만원"].sum() + df["회수금액_백만원"].sum()) > 0 else 0
            st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e5e5e5;border-radius:10px;padding:20px 24px;">
  <div style="display:flex;gap:24px;">
    <div>
      <div style="font-size:36px;font-weight:800;color:#1a1a1a;">{avg_years}<span style="font-size:16px;color:#999;">년</span></div>
      <div style="font-size:12px;color:#999;">평균 투자 기간</div>
    </div>
    <div>
      <div style="font-size:36px;font-weight:800;color:#1b5e20;">{realized_pct}<span style="font-size:16px;color:#999;">%</span></div>
      <div style="font-size:12px;color:#999;">실현 비율</div>
    </div>
  </div>
  <div style="margin-top:12px;background:#f0f0f0;border-radius:6px;height:8px;overflow:hidden;">
    <div style="width:{realized_pct}%;height:100%;background:#1b5e20;border-radius:6px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;">
    <span style="font-size:9px;color:#ccc;">미실현</span>
    <span style="font-size:9px;color:#ccc;">전액 실현</span>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Charts ────────────────────────────────────
        st.markdown("#### Charts")

        # ── 초록 인포그래픽 차트 팔레트 ──────────────
        _GP = ["#1b5e20","#2e7d32","#43a047","#66bb6a","#81c784","#a5d6a7","#c8e6c9","#e8f5e9"]
        _CHART = dict(
            height=300, margin=dict(t=30,b=20,l=20,r=20),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
        )
        _GRID  = dict(showgrid=True, gridcolor="#f0f0f0", gridwidth=1, zeroline=False)
        _NOGRID = dict(showgrid=False, zeroline=False)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">MOIC Distribution</p>', unsafe_allow_html=True)
            fig_bar = px.bar(
                result_df.sort_values("MOIC", ascending=False),
                x="회사명", y="MOIC", color="섹터",
                color_discrete_sequence=_GP,
                labels={"MOIC": "MOIC (x)", "회사명": ""},
            )
            fig_bar.add_hline(y=1.0, line_dash="dot", line_color="#c8e6c9",
                              annotation_text="1.0x", annotation_font_color="#81c784",
                              annotation_font_size=10)
            fig_bar.update_traces(marker_line_width=0, opacity=0.9)
            fig_bar.update_layout(**_CHART,
                                  legend=dict(font_size=10, orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)"),
                                  bargap=0.55)
            fig_bar.update_xaxes(**_NOGRID, tickfont_size=10)
            fig_bar.update_yaxes(**_GRID, tickfont_size=10)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">MOIC vs IRR</p>', unsafe_allow_html=True)
            max_size = result_df["투자금액_백만원"].max()
            fig_sc = px.scatter(
                result_df, x="IRR(%)", y="MOIC",
                text="회사명", color="섹터", size="투자금액_백만원",
                color_discrete_sequence=_GP, size_max=55,
            )
            fig_sc.update_traces(
                textposition="top center", textfont_size=10, textfont_color="#666",
                marker=dict(sizeref=2.0*max_size/(55**2), sizemode="area", opacity=0.75,
                            line=dict(width=1, color="#ffffff")),
            )
            fig_sc.add_hline(y=1.0, line_dash="dot", line_color="#e8f5e9")
            fig_sc.add_vline(x=0, line_dash="dot", line_color="#e8f5e9")
            fig_sc.update_layout(**_CHART,
                                  legend=dict(font_size=10, orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)"))
            fig_sc.update_xaxes(**_GRID, tickfont_size=10)
            fig_sc.update_yaxes(**_GRID, tickfont_size=10)
            st.plotly_chart(fig_sc, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">Sector Allocation</p>', unsafe_allow_html=True)
            sector_df = df.groupby("섹터")["투자금액_백만원"].sum().reset_index()
            fig_pie = px.pie(sector_df, names="섹터", values="투자금액_백만원",
                             color_discrete_sequence=_GP)
            fig_pie.update_traces(
                textinfo="label+percent", hole=0.5, textfont_size=11,
                marker_line_width=2, marker_line_color="#ffffff",
                pull=[0.02]*len(sector_df),
            )
            fig_pie.update_layout(
                height=300, margin=dict(t=10,b=10), showlegend=False,
                paper_bgcolor="#ffffff", font=dict(color="#1a1a1a"),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_d:
            st.markdown('<p style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#1b5e20;font-weight:700;margin-bottom:6px;">Investment & MOIC Treemap</p>', unsafe_allow_html=True)
            fig_tree = px.treemap(
                result_df, path=["섹터","회사명"],
                values="투자금액_백만원", color="MOIC",
                color_continuous_scale=["#e8f5e9","#66bb6a","#2e7d32","#1b5e20"],
                hover_data={"IRR(%)": True, "TVPI": True},
            )
            fig_tree.update_traces(
                textinfo="label+value", textfont_size=11,
                marker_line_width=2, marker_line_color="#ffffff",
            )
            fig_tree.update_layout(
                height=300, margin=dict(t=10,b=0),
                paper_bgcolor="#ffffff",
                coloraxis_colorbar=dict(title="MOIC", thickness=12, len=0.5),
            )
            st.plotly_chart(fig_tree, use_container_width=True)




# ── TAB 2: Portfolio ──────────────────────────────
with tab2:
    st.caption("J-Curve 현금흐름 추이  |  분기별 TVPI·DPI·RVPI 변화 추적")

    with st.expander("J-Curve란?"):
        st.markdown("""
사모펀드·VC 펀드는 초기에 투자 집행으로 **누적 현금흐름이 마이너스(−)**로 진입합니다.
이후 포트폴리오사 가치가 성장해 회수가 이뤄지면 플러스(+)로 전환되는데,
이 흐름이 알파벳 **'J'자 형태**를 그려 J-Curve라고 부릅니다.
""")

    cf_upload = st.file_uploader("현금흐름 CSV 업로드", type="csv", key="cf")
    load_cf_sample = st.button("샘플 현금흐름 불러오기")

    cf_df = None
    if cf_upload:
        cf_df = pd.read_csv(cf_upload)
    elif load_cf_sample:
        try:
            cf_df = pd.read_csv("sample_cashflows.csv")
            st.success("샘플 현금흐름 로드됨")
        except FileNotFoundError:
            st.error("sample_cashflows.csv 파일이 없습니다.")

    if cf_df is not None:
        trend = j_curve_data(cf_df)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend["날짜"], y=trend["누적현금흐름"],
            mode="lines+markers", name="누적 순현금흐름",
            line=dict(color="#2e7d32", width=3, shape="spline"),
            fill="tozeroy", fillcolor="rgba(200,230,201,0.3)",
            marker=dict(color="#1b5e20", size=8, line=dict(width=2, color="#ffffff")),
        ))
        fig.add_hline(y=0, line_dash="dot", line_color="#c8e6c9",
                      annotation_text="Break-even",
                      annotation_font_color="#81c784", annotation_font_size=10)
        fig.update_layout(
            height=350, margin=dict(t=30,b=20,l=20,r=20),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
            xaxis_title="", yaxis_title="누적 순현금흐름 (백만원)",
        )
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont_size=10)
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False, tickfont_size=10)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("컬럼: 회사명, 날짜(YYYY-MM-DD), 현금흐름_백만원 — 투자=음수, 배당·회수=양수")

        st.divider()
        if st.button("J-Curve 보고서 생성", key="jcurve_pdf"):
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_jcurve(trend)
                pdf_bytes = generate_jcurve_pdf(trend, ai_text, quarter)
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"jcurve_{quarter or 'report'}.pdf",
                mime="application/pdf",
            )
    else:
        st.info("현금흐름 CSV를 업로드하거나 샘플을 불러오세요.")

    # ── 분기별 추이 섹션 ───────────────────────────
    st.markdown("---")
    st.markdown("### 분기별 펀드 지표 추이")
    quarters = load_quarters()
    if not quarters:
        st.info("저장된 분기 데이터가 없습니다.\n\n데이터 로드 후 사이드바에서 [현재 데이터 저장]을 눌러 분기를 누적하세요.")
    else:
        trend_df = load_trend()
        _LINE_COLORS = {"TVPI": "#1b5e20", "DPI": "#43a047", "RVPI": "#a5d6a7"}
        fig_q = go.Figure()
        for metric in ["TVPI", "DPI", "RVPI"]:
            fig_q.add_trace(go.Scatter(
                x=trend_df["quarter"], y=trend_df[metric],
                mode="lines+markers", name=metric,
                line=dict(color=_LINE_COLORS[metric], width=3, shape="spline"),
                marker=dict(color=_LINE_COLORS[metric], size=9,
                            line=dict(width=2, color="#ffffff")),
            ))
        fig_q.update_layout(
            height=350, margin=dict(t=30,b=20,l=20,r=20),
            xaxis_title="", yaxis_title="배수 (x)",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
            legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font_size=11),
        )
        fig_q.update_xaxes(showgrid=False, zeroline=False, tickfont_size=10)
        fig_q.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False, tickfont_size=10)
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(trend_df, use_container_width=True)

        st.divider()
        if st.button("분기 추이 보고서 생성", key="trend_pdf"):
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_quarterly_trend(trend_df)
                pdf_bytes = generate_quarterly_pdf(trend_df, ai_text, quarter)
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"quarterly_trend_{quarter or 'report'}.pdf",
                mime="application/pdf",
            )

# ── TAB 3: Market ────────────────────────────────
with tab3:
    st.caption("DART 재무 조회  |  시나리오 시뮬레이터  |  IRR Sensitivity  |  Waterfall 분배")

    # ── ① DART 재무 조회 ────────────────────────────
    st.markdown("### DART 기업 재무 조회")
    corp_name = st.text_input("기업명 입력 (예: 삼성전자, 카카오)")

    if st.button("검색", key="dart_search") and corp_name:
        with st.spinner("DART에서 검색 중..."):
            results = search_company(corp_name)
        if results:
            st.session_state["dart_results"] = results
            st.session_state["dart_fin_df"] = None
        else:
            st.warning("검색 결과가 없습니다.")

    if "dart_results" in st.session_state and st.session_state["dart_results"]:
        options = {r["corp_name"]: r["corp_code"] for r in st.session_state["dart_results"]}
        selected = st.selectbox("기업 선택", list(options.keys()))

        if st.button("재무제표 조회", key="dart_fin"):
            with st.spinner("재무제표 불러오는 중..."):
                fin_df = get_financials(options[selected])
            if not fin_df.empty:
                st.session_state["dart_fin_df"] = fin_df
                st.session_state["dart_selected"] = selected
            else:
                st.warning("재무 데이터를 불러올 수 없습니다.")

        if st.session_state.get("dart_fin_df") is not None:
            fin_df = st.session_state["dart_fin_df"]
            selected_name = st.session_state.get("dart_selected", selected)
            st.dataframe(fin_df, use_container_width=True)
            fig_dart = px.bar(
                fin_df.melt(id_vars="연도", value_vars=["매출액", "영업이익", "당기순이익"]),
                x="연도", y="value", color="variable", barmode="group",
                color_discrete_sequence=["#1b5e20", "#43a047", "#c8e6c9"],
                labels={"value": "금액 (원)", "variable": ""},
            )
            fig_dart.update_traces(marker_line_width=0, opacity=0.9)
            fig_dart.update_layout(
                height=320, margin=dict(t=20,b=20,l=20,r=20),
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
                legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font_size=10),
                bargap=0.5,
            )
            fig_dart.update_xaxes(showgrid=False, zeroline=False)
            fig_dart.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False)
            st.plotly_chart(fig_dart, use_container_width=True)

            st.divider()
            if st.button("DART 재무분석 보고서 생성", key="dart_pdf"):
                with st.spinner("AI 해석 생성 중..."):
                    ai_text = interpret_dart_financials(selected_name, fin_df)
                    pdf_bytes = generate_dart_pdf(selected_name, fin_df, ai_text, quarter)
                st.text_area("AI 해석 미리보기", ai_text, height=200)
                st.download_button(
                    "PDF 다운로드", pdf_bytes,
                    file_name=f"dart_{selected_name}_{quarter or 'report'}.pdf",
                    mime="application/pdf",
                )

    # ── ② 시나리오 시뮬레이터 ───────────────────────
    st.markdown("---")
    st.markdown("### 회수 시나리오 시뮬레이터")
    if "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        df        = st.session_state["df"]
        company2  = st.selectbox("포트폴리오사 선택", result_df["회사명"].tolist(), key="sim_company")
        r2        = result_df[result_df["회사명"] == company2].iloc[0]
        raw_r2    = df[df["회사명"] == company2].iloc[0]

        left2, right2 = st.columns([1, 2])
        with left2:
            st.metric("투자금액",      f"{int(raw_r2['투자금액_백만원']):,}백만원")
            st.metric("현재 MOIC",     f"{r2['MOIC']}x")
            st.metric("현재 IRR",      f"{r2['IRR(%)']}%")
            target_irr2 = st.slider("목표 IRR (%)", 10, 40, 20, key="sim_irr")
            opt2 = optimal_exit_timing(
                raw_r2["투자금액_백만원"], raw_r2["현재가치_백만원"],
                raw_r2["투자일"], target_irr2,
            )
            st.info(
                f"목표 IRR {target_irr2}% 달성 최소 배수: **{opt2[f'IRR {target_irr2}% 달성 최소 배수']}x**\n\n"
                f"{opt2['목표 달성 여부']}"
            )
        with right2:
            sim_df2 = simulate_exit(
                raw_r2["투자금액_백만원"], raw_r2["투자일"],
                [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
            )
            fig_sim2 = px.bar(
                sim_df2, x="Exit 배수", y="IRR (%)",
                color="IRR (%)", color_continuous_scale=["#e8f5e9","#66bb6a","#2e7d32","#1b5e20"],
                text="IRR (%)",
            )
            fig_sim2.add_hline(
                y=target_irr2, line_dash="dot", line_color="#a5d6a7",
                annotation_text=f"Target {target_irr2}%",
                annotation_font_color="#66bb6a", annotation_font_size=10,
            )
            fig_sim2.update_traces(texttemplate="%{text}%", textposition="outside",
                                   marker_line_width=0)
            fig_sim2.update_layout(
                height=320, margin=dict(t=20,b=20,l=20,r=20),
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
                bargap=0.3, showlegend=False,
            )
            fig_sim2.update_xaxes(showgrid=False, zeroline=False)
            fig_sim2.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False)
            st.plotly_chart(fig_sim2, use_container_width=True)
            st.dataframe(sim_df2, use_container_width=True)

        st.divider()
        if st.button("시나리오 보고서 생성", key="sim_pdf"):
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_scenario(company2, sim_df2, opt2)
                pdf_bytes = generate_scenario_pdf(company2, sim_df2, opt2, ai_text, quarter)
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button("PDF 다운로드", pdf_bytes,
                               file_name=f"scenario_{company2}_{quarter or 'report'}.pdf",
                               mime="application/pdf")

    # ── ③ IRR Sensitivity Matrix ────────────────────
    st.markdown("---")
    st.markdown("### IRR Sensitivity Matrix")
    st.caption("Exit 타이밍(년) × Exit 배수 조합별 예상 IRR — 엑셀로는 수작업이 필요한 분석")

    if "df" not in st.session_state:
        st.info("대시보드에서 데이터를 먼저 로드하세요.")
    else:
        mat_company = st.selectbox(
            "분석 기업 선택", st.session_state["result_df"]["회사명"].tolist(), key="mat_co"
        )
        mat_raw = st.session_state["df"]
        mat_raw = mat_raw[mat_raw["회사명"] == mat_company].iloc[0]
        invested = float(mat_raw["투자금액_백만원"])

        multiples = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        years_list = list(range(1, 11))

        matrix = []
        for m in multiples:
            row = []
            for y in years_list:
                irr = round((m ** (1 / y) - 1) * 100, 1)
                row.append(irr)
            matrix.append(row)

        mat_df = pd.DataFrame(matrix, index=[f"{m}x" for m in multiples],
                              columns=[f"{y}년" for y in years_list])

        fig_mat = go.Figure(data=go.Heatmap(
            z=matrix,
            x=[f"{y}년" for y in years_list],
            y=[f"{m}x" for m in multiples],
            colorscale=[
                [0.0,  "#d32f2f"], [0.15, "#e53935"],
                [0.3,  "#ff9800"], [0.45, "#ffc107"],
                [0.55, "#cddc39"], [0.7,  "#66bb6a"],
                [0.85, "#43a047"], [1.0,  "#1b5e20"],
            ],
            zmid=15,
            text=[[f"{v}%" for v in row] for row in matrix],
            texttemplate="%{text}",
            textfont=dict(size=10, color="#ffffff"),
            hovertemplate="Exit %{y} · %{x}<br>IRR: %{z:.1f}%<extra></extra>",
        ))
        fig_mat.update_layout(
            xaxis_title="", yaxis_title="",
            height=400, margin=dict(t=20, b=20, l=20, r=20),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
        )
        st.plotly_chart(fig_mat, use_container_width=True)
        st.caption("초록 = IRR 높음 / 빨강 = IRR 낮음 · 기준선 15% (일반적인 PE 목표 IRR)")

    # ── ④ Waterfall 계산기 ──────────────────────────
    st.markdown("---")
    st.markdown("### Waterfall 분배 계산기")
    with st.expander("Waterfall이란?"):
        st.markdown("""
PE 펀드 회수금을 **LP → GP 순서로 단계별 분배**하는 구조입니다.
① 원금 반환 → ② Hurdle Rate 우선수익 → ③ GP 캐치업 → ④ 초과수익 분배 (Carried Interest).
GP는 Hurdle을 넘어야 Carry를 받을 수 있어 LP 이익 보호 장치로 작동합니다.
""")

    if "result_df" in st.session_state and st.button("현재 포트폴리오 데이터로 자동 채움", key="wf_auto"):
        _df = st.session_state["df"]
        st.session_state["wf_auto_inv"] = int(_df["투자금액_백만원"].sum())
        st.session_state["wf_auto_proc"] = int(_df["현재가치_백만원"].sum() + _df["회수금액_백만원"].sum())
        st.rerun()

    _auto_inv = st.session_state.get("wf_auto_inv", 10000)
    _auto_proc = st.session_state.get("wf_auto_proc", 18000)

    wf_c1, wf_c2, wf_c3 = st.columns(3)
    with wf_c1:
        wf_invested   = st.number_input("총 투자금액 (백만원)", min_value=100, value=_auto_inv, step=100, key="wf_inv")
        wf_proceeds   = st.number_input("총 회수금액 (백만원)", min_value=100, value=_auto_proc, step=100, key="wf_proc")
        wf_years      = st.number_input("펀드 기간 (년)", min_value=1, max_value=20, value=5, key="wf_years")
    with wf_c2:
        wf_hurdle     = st.slider("Hurdle Rate (%)", 0, 20, 8, key="wf_hurdle")
        wf_catchup    = st.slider("GP 캐치업율 (%)", 0, 100, 100, key="wf_catchup",
                                   help="100% = GP가 먼저 독식하며 catch-up / 50% = LP·GP 반반 분담")
    with wf_c3:
        wf_carry      = st.slider("Carried Interest (%)", 0, 30, 20, key="wf_carry")
        st.markdown("""
<div style="font-size:12px;color:#666;line-height:1.6;margin-top:8px;">
  <b>Hurdle Rate</b>: LP 우선수익률 (보통 8%)<br>
  <b>캐치업율</b>: GP가 Carry 몫을 따라잡는 속도<br>
  <b>Carried Interest</b>: GP 성과보수 비율 (보통 20%)
</div>
""", unsafe_allow_html=True)

    if st.button("Waterfall 계산", key="wf_calc", type="primary"):
        total_profit = max(0.0, float(wf_proceeds) - float(wf_invested))
        remaining    = float(wf_proceeds)
        steps        = []

        # ① 원금 반환
        lp1  = min(remaining, float(wf_invested))
        remaining -= lp1
        steps.append({"단계": "① 원금 반환", "LP": lp1, "GP": 0.0,
                       "누적 LP": lp1, "누적 GP": 0.0,
                       "설명": f"LP 투자원금 {wf_invested:,}백만원 전액 반환"})

        # ② 우선수익 (Hurdle)
        hurdle_amt = float(wf_invested) * ((1 + wf_hurdle/100) ** wf_years - 1)
        lp2  = min(remaining, hurdle_amt)
        remaining -= lp2
        steps.append({"단계": "② 우선수익 (Hurdle)", "LP": lp2, "GP": 0.0,
                       "누적 LP": lp1+lp2, "누적 GP": 0.0,
                       "설명": f"연 {wf_hurdle}% 복리 × {wf_years}년 → {hurdle_amt:,.0f}백만원 (실수취 {lp2:,.0f})"})

        # ③ GP 캐치업
        gp_carry_target = total_profit * wf_carry / 100
        if wf_catchup > 0 and remaining > 0 and gp_carry_target > 0:
            catchup_pool = min(remaining, gp_carry_target / (wf_catchup / 100))
            gp3  = catchup_pool * wf_catchup / 100
            lp3  = catchup_pool - gp3
            remaining -= catchup_pool
        else:
            gp3, lp3 = 0.0, 0.0
        steps.append({"단계": "③ GP 캐치업", "LP": lp3, "GP": gp3,
                       "누적 LP": lp1+lp2+lp3, "누적 GP": gp3,
                       "설명": f"GP Carry 목표 {gp_carry_target:,.0f}백만원 → {gp3:,.0f}백만원 확보 (캐치업율 {wf_catchup}%)"})

        # ④ 초과수익 분배
        gp4  = remaining * wf_carry / 100
        lp4  = remaining - gp4
        steps.append({"단계": "④ 초과수익 분배", "LP": lp4, "GP": gp4,
                       "누적 LP": lp1+lp2+lp3+lp4, "누적 GP": gp3+gp4,
                       "설명": f"LP {100-wf_carry}% ({lp4:,.0f}) / GP {wf_carry}% ({gp4:,.0f})"})

        total_lp = lp1+lp2+lp3+lp4
        total_gp = gp3+gp4
        eff_carry = total_gp/total_profit*100 if total_profit > 0 else 0

        # 요약 지표
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 투자금액", f"{wf_invested:,}백만원")
        m2.metric("총 회수금액", f"{wf_proceeds:,}백만원")
        m3.metric("LP 최종 수취", f"{total_lp:,.0f}백만원",
                  delta=f"MOIC {total_lp/wf_invested:.2f}x")
        m4.metric("GP Carry 수취", f"{total_gp:,.0f}백만원",
                  delta=f"실효 Carry {eff_carry:.1f}%")

        st.markdown("##### 단계별 분배 내역")
        step_df = pd.DataFrame(steps)[["단계","LP","GP","설명"]]
        step_df["LP"] = step_df["LP"].apply(lambda x: f"{x:,.0f}")
        step_df["GP"] = step_df["GP"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(step_df, use_container_width=True, hide_index=True)

        # 누적 Waterfall 차트
        st.markdown("##### Waterfall 시각화")
        wf_chart_df = pd.DataFrame(steps)
        fig_wf = go.Figure()
        fig_wf.add_trace(go.Bar(
            name="LP", x=wf_chart_df["단계"], y=wf_chart_df["LP"],
            marker_color="#1b5e20", text=wf_chart_df["LP"].apply(lambda x: f"{x:,.0f}"),
            textposition="inside", insidetextanchor="middle",
            marker_line_width=0,
        ))
        fig_wf.add_trace(go.Bar(
            name="GP", x=wf_chart_df["단계"], y=wf_chart_df["GP"],
            marker_color="#a5d6a7", text=wf_chart_df["GP"].apply(lambda x: f"{x:,.0f}" if x>0 else ""),
            textposition="inside", insidetextanchor="middle",
            marker_line_width=0,
        ))
        fig_wf.update_layout(
            barmode="stack", height=350,
            yaxis_title="금액 (백만원)",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
            legend=dict(orientation="h", y=1.02, bgcolor="rgba(0,0,0,0)", font_size=11),
            margin=dict(t=40, b=10, l=20, r=20), bargap=0.3,
        )
        fig_wf.update_xaxes(showgrid=False, zeroline=False, tickfont_size=10)
        fig_wf.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False, tickfont_size=10)
        st.plotly_chart(fig_wf, use_container_width=True)

        # LP vs GP 최종 파이
        col_pie, col_txt = st.columns([1, 1])
        with col_pie:
            fig_pie = px.pie(
                values=[total_lp, total_gp],
                names=["LP", "GP"],
                color_discrete_sequence=["#1b5e20", "#c8e6c9"],
                hole=0.5,
            )
            fig_pie.update_traces(
                textinfo="label+percent+value",
                texttemplate="%{label}<br>%{percent}<br>%{value:,.0f}M",
                marker_line_width=2, marker_line_color="#ffffff",
            )
            fig_pie.update_layout(
                showlegend=False, margin=dict(t=20, b=0),
                paper_bgcolor="#ffffff",
                font=dict(family="Pretendard, sans-serif", color="#1a1a1a", size=12),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_txt:
            st.metric("총 수익", f"{total_profit:,.0f}M")
            st.metric("LP 순수익", f"{total_lp-wf_invested:,.0f}M")
            st.metric("GP Carry", f"{total_gp:,.0f}M", delta=f"수익의 {eff_carry:.1f}%")
            st.markdown(f"""
**LP MOIC** {total_lp/wf_invested:.2f}x · **GP 실효 Carry** {eff_carry:.1f}%

<span style="font-size:11px;color:#999;">Hurdle {wf_hurdle}% · 캐치업 {wf_catchup}% · Carry {wf_carry}% · {wf_years}년</span>
""", unsafe_allow_html=True)

# ── TAB 4: Tools ─────────────────────────────────
with tab4:
    st.caption("ECOS 거시지표  |  KVIC 벤치마크  |  기준금리·환율 스프레드")
    st.markdown("### 거시지표 — 기준금리 & 환율 (ECOS)")

    # ECOS 섹션
    st.markdown("#### 한국은행 기준금리 & 원/달러 환율")
    months = st.slider("조회 기간 (개월)", 6, 36, 24, key="ecos_months")

    if st.button("거시지표 불러오기"):
        with st.spinner("기준금리 조회 중..."):
            rate_df = get_base_rate(months)
        with st.spinner("환율 조회 중..."):
            fx_df = get_exchange_rate(months)
        st.session_state["macro_rate_df"] = rate_df
        st.session_state["macro_fx_df"] = fx_df

    rate_df = st.session_state.get("macro_rate_df", None)
    fx_df = st.session_state.get("macro_fx_df", None)

    if rate_df is not None or fx_df is not None:
        col1, col2 = st.columns(2)
        spread = None

        with col1:
            if rate_df is not None and not rate_df.empty:
                fig = px.line(rate_df, x="기간", y="기준금리(%)",
                              title="한국은행 기준금리 (%)", markers=True,
                              color_discrete_sequence=["#2e7d32"])
                fig.update_traces(line=dict(color="#2e7d32"), marker=dict(color="#2e7d32"))
                fig.update_layout(
                    xaxis_title="월", yaxis_title="금리 (%)",
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
                )
                fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
                fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
                st.plotly_chart(fig, use_container_width=True)

                latest_rate = rate_df["기준금리(%)"].iloc[-1]
                st.metric("현재 기준금리", f"{latest_rate}%")

                if "result_df" in st.session_state:
                    avg_irr = st.session_state["result_df"]["IRR(%)"].mean()
                    spread = round(avg_irr - latest_rate, 2)
                    st.metric(
                        "펀드 평균 IRR vs 기준금리 스프레드",
                        f"{spread:+.1f}%p",
                        delta=f"기준금리 {latest_rate}% 대비",
                    )
            else:
                st.warning("기준금리 데이터를 불러올 수 없습니다.")

        with col2:
            if fx_df is not None and not fx_df.empty:
                fig2 = px.line(fx_df, x="기간", y="원/달러(원)",
                               title="원/달러 환율 월평균", markers=True,
                               color_discrete_sequence=["#2e7d32"])
                fig2.update_traces(line=dict(color="#2e7d32"), marker=dict(color="#2e7d32"))
                fig2.update_layout(
                    xaxis_title="월", yaxis_title="환율 (원)",
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
                )
                fig2.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
                fig2.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
                st.plotly_chart(fig2, use_container_width=True)
                latest_fx = fx_df["원/달러(원)"].iloc[-1]
                st.metric("현재 원/달러", f"{latest_fx:,.0f}원")
            else:
                st.warning("환율 데이터를 불러올 수 없습니다.")

        st.divider()
        if st.button("거시지표 보고서 생성", key="macro_pdf"):
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_macro(
                    rate_df if rate_df is not None else pd.DataFrame(),
                    fx_df if fx_df is not None else pd.DataFrame(),
                    spread,
                )
                pdf_bytes = generate_macro_pdf(
                    rate_df if rate_df is not None else pd.DataFrame(),
                    fx_df if fx_df is not None else pd.DataFrame(),
                    ai_text, spread, quarter,
                )
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"macro_{quarter or 'report'}.pdf",
                mime="application/pdf",
            )

    st.divider()

    # ── KVIC 한국벤처투자 섹션
    st.markdown("---")
    st.markdown("### 한국벤처투자(KVIC) 모태펀드 벤치마크")

    import os
    if not os.getenv("KVIC_API_KEY"):
        st.info("KVIC_API_KEY가 없습니다. `.env`에 `KVIC_API_KEY=키값` 추가 후 재시작하세요.")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            kvic_year = st.selectbox(
                "조회 연도", list(range(2023, 2003, -1)), index=0, key="kvic_year"
            )
        with col_r:
            st.write("")
            load_kvic = st.button("KVIC 데이터 불러오기", key="kvic_load")

        if load_kvic:
            with st.spinner("한국벤처투자 API 조회 중..."):
                sector_df = get_kvic_sector_summary(kvic_year)
                trend_df_kvic = get_kvic_yearly_trend()
            st.session_state["kvic_sector"] = sector_df
            st.session_state["kvic_trend"] = trend_df_kvic

        if "kvic_sector" in st.session_state and not st.session_state["kvic_sector"].empty:
            sector_df = st.session_state["kvic_sector"]
            trend_df_kvic = st.session_state.get("kvic_trend", pd.DataFrame())

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**{kvic_year}년 분야별 조합 현황 (상위 15)**")
                top15 = sector_df.head(15)
                fig_s = px.bar(
                    top15, x="총약정액(억원)", y="투자분야",
                    orientation="h", color="조합수",
                    color_continuous_scale="Greens",
                    title=f"{kvic_year}년 모태펀드 분야별 약정액",
                    labels={"총약정액(억원)": "약정액 (억원)", "투자분야": ""},
                )
                fig_s.update_layout(
                    yaxis=dict(autorange="reversed"), height=420,
                    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
                )
                st.plotly_chart(fig_s, use_container_width=True)

                total_funds = sector_df["조합수"].sum()
                total_amt = sector_df["총약정액(억원)"].sum()
                st.metric("전체 조합 수", f"{total_funds:,}개")
                st.metric("총 약정액", f"{total_amt:,}억원")

            with col2:
                if not trend_df_kvic.empty:
                    st.markdown("**연도별 결성 추이 (2019~)**")
                    fig_t = px.bar(
                        trend_df_kvic, x="결성연도", y="총약정액(억원)",
                        color="결성조합수", color_continuous_scale="Greens",
                        title="연도별 모태펀드 결성 규모",
                        text="결성조합수",
                    )
                    fig_t.update_traces(texttemplate="%{text}개", textposition="outside")
                    fig_t.update_layout(
                        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
                    )
                    st.plotly_chart(fig_t, use_container_width=True)

                # 포트폴리오 섹터와 시장 비교
                if "result_df" in st.session_state:
                    st.markdown("**내 포트폴리오 섹터 vs 시장 분야 매핑**")
                    my_sectors = st.session_state["result_df"]["섹터"].value_counts().reset_index()
                    my_sectors.columns = ["섹터", "투자기업수"]
                    st.dataframe(my_sectors, use_container_width=True)
                    st.caption("↑ 내 포트폴리오 섹터 비중 (KVIC 분야와 비교)")

            st.divider()
            with st.expander("전체 분야별 데이터 보기"):
                st.dataframe(sector_df, use_container_width=True)

# ── TAB 5: Report ────────────────────────────────
with tab5:
    st.markdown("### Report Builder")
    st.caption("포함할 섹션을 선택하고 LP 보고서(PDF) 또는 IC 장표(PPTX)를 생성하세요.")

    if "result_df" in st.session_state:
        result_df = st.session_state["result_df"]
        df        = st.session_state["df"]
        summary   = st.session_state["summary"]

        # multiselect 스타일
        st.markdown("""<style>
span[data-baseweb="tag"] { background-color:#e8dcc8 !important; color:#1a1a1a !important;
    font-size:11px !important; height:26px !important; border-radius:6px !important; padding:0 8px !important; }
span[data-baseweb="tag"] span { color:#1a1a1a !important; }
span[data-baseweb="tag"] svg { fill:#999 !important; width:12px !important; }
</style>""", unsafe_allow_html=True)

        # 가이드 카드
        st.markdown("""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;">
  <div style="background:#fafafa;border-radius:8px;padding:10px 14px;">
    <div style="font-size:10px;color:#1b5e20;font-weight:700;letter-spacing:0.08em;margin-bottom:4px;">OVERVIEW</div>
    <div style="font-size:10px;color:#999;line-height:1.5;">성과 요약 · 포트폴리오 상세<br>Top/Bottom · 섹터 · 집중도 · 리스크</div>
  </div>
  <div style="background:#fafafa;border-radius:8px;padding:10px 14px;">
    <div style="font-size:10px;color:#1b5e20;font-weight:700;letter-spacing:0.08em;margin-bottom:4px;">PORTFOLIO · ANALYSIS</div>
    <div style="font-size:10px;color:#999;line-height:1.5;">J-Curve · 분기 추이<br>DART 재무 · 시나리오 · Waterfall</div>
  </div>
  <div style="background:#fafafa;border-radius:8px;padding:10px 14px;">
    <div style="font-size:10px;color:#1b5e20;font-weight:700;letter-spacing:0.08em;margin-bottom:4px;">BENCHMARK · AI</div>
    <div style="font-size:10px;color:#999;line-height:1.5;">거시지표 (금리·환율)<br>AI 코멘터리 · 뉴스 모니터링</div>
  </div>
</div>
""", unsafe_allow_html=True)

        all_sections = [
            "성과 요약 (MOIC·IRR·DPI·RVPI·TVPI)", "포트폴리오 상세",
            "Top/Bottom 성과 분석", "섹터별 투자 비중",
            "집중도·투자기간·실현율", "리스크 평가", "AI 코멘터리",
            "J-Curve 현금흐름", "분기별 추이", "거시지표 (금리·환율)",
            "Waterfall 분배", "시나리오 분석", "IRR Sensitivity", "뉴스 모니터링",
        ]
        selected = st.multiselect("포함할 섹션", all_sections, default=all_sections[:7])
        st.session_state["report_sections"] = selected

        st.markdown("---")

        # 출력 버튼
        fmt1, fmt2, fmt3 = st.columns(3)
        with fmt1:
            if st.button("LP 보고서 (PDF)", use_container_width=True, type="primary"):
                with st.spinner("PDF 생성 중..."):
                    detail_rows = result_df[["회사명","MOIC","IRR(%)","TVPI","투자금액_백만원"]].to_dict("records")
                    _comm = generate_commentary(summary, detail_rows) if "AI" in str(selected) else ""
                    _jc = st.session_state.get("jcurve_trend") if "J-Curve" in str(selected) else None
                    _tr = None
                    if "분기별" in str(selected):
                        from db import load_quarters, load_trend
                        if load_quarters(): _tr = load_trend()
                    _rate = st.session_state.get("macro_rate_df") if "거시" in str(selected) else None
                    _fx = st.session_state.get("macro_fx_df") if "거시" in str(selected) else None
                    pdf_bytes = generate_full_pdf(
                        summary, result_df, df, _comm, quarter,
                        fund_name=fund_name, fund_strategy=fund_strategy, base_date=base_date,
                        jcurve_df=_jc, trend_df=_tr, rate_df=_rate, fx_df=_fx,
                        spread=st.session_state.get("macro_spread"))
                st.download_button("PDF 다운로드", pdf_bytes, file_name=f"LP_Report_{quarter}.pdf",
                                   mime="application/pdf", use_container_width=True)
        with fmt2:
            if st.button("IC 장표 (PPTX)", use_container_width=True):
                with st.spinner("PPTX 생성 중..."):
                    from report_pptx import generate_lp_pptx
                    _comm = generate_commentary(summary,
                        result_df[["회사명","MOIC","IRR(%)","TVPI","투자금액_백만원"]].to_dict("records")) if "AI" in str(selected) else ""
                    pptx_bytes = generate_lp_pptx(summary, result_df, _comm, quarter,
                        fund_name=fund_name, fund_strategy=fund_strategy, base_date=base_date)
                st.download_button("PPTX 다운로드", pptx_bytes, file_name=f"IC_Report_{quarter}.pptx",
                                   mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                   use_container_width=True)
        with fmt3:
            if st.button("데이터 (Excel)", use_container_width=True):
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                excel_buf = io.BytesIO()
                sel = str(selected)
                with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                    result_df.to_excel(writer, sheet_name="Portfolio", index=False)
                    if "Top" in sel:
                        sm = result_df.sort_values("MOIC", ascending=False)
                        t = sm.head(3)[["회사명","섹터","MOIC","IRR(%)","TVPI"]].copy(); t.insert(0,"구분",["Top1","Top2","Top3"])
                        b = sm.tail(3)[["회사명","섹터","MOIC","IRR(%)","TVPI"]].copy(); b.insert(0,"구분",["Bot1","Bot2","Bot3"])
                        pd.concat([t,b]).to_excel(writer, sheet_name="Top_Bottom", index=False)
                    if "섹터" in sel:
                        sa = result_df.groupby("섹터").agg(기업수=("회사명","count"),평균MOIC=("MOIC","mean"),평균IRR=("IRR(%)","mean")).round(2).reset_index()
                        sa.to_excel(writer, sheet_name="Sector", index=False)
                    if "집중" in sel:
                        w = df["투자금액_백만원"]/df["투자금액_백만원"].sum()
                        hhi = round((w**2).sum()*10000)
                        pd.DataFrame({"지표":["HHI","판정","평균투자기간(년)","실현율(%)"],
                            "값":[hhi,"High" if hhi>2500 else "Low",round((pd.to_datetime(df["기준일"])-pd.to_datetime(df["투자일"])).dt.days.mean()/365.25,1),
                                  round(df["회수금액_백만원"].sum()/(df["현재가치_백만원"].sum()+df["회수금액_백만원"].sum())*100,1)]
                        }).to_excel(writer, sheet_name="Analytics", index=False)
                    df.to_excel(writer, sheet_name="Raw Data", index=False)
                    wb = writer.book
                    gf = PatternFill(start_color="1B5E20",end_color="1B5E20",fill_type="solid")
                    wf = Font(name="맑은 고딕",bold=True,color="FFFFFF",size=11)
                    for sn in wb.sheetnames:
                        ws = wb[sn]
                        for cell in ws[1]: cell.fill=gf; cell.font=wf; cell.alignment=Alignment(horizontal="center")
                        for col in ws.columns:
                            cl=col[0].column_letter
                            mx=max(sum(2 if ord(c)>127 else 1 for c in str(cell.value or "")) for cell in col)
                            ws.column_dimensions[cl].width=min(mx+4,45)
                st.download_button("Excel 다운로드", excel_buf.getvalue(), file_name=f"Data_{quarter}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)

        st.markdown("---")
        st.caption("본 보고서는 참고용 자료이며, 투자 결정의 근거로 단독 사용할 수 없습니다.")

    st.markdown("---")
    st.markdown("### AI 분석")
    if "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        summary   = st.session_state["summary"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 분기 코멘터리")
            st.caption("포트폴리오 전체를 LP 보고서 형식으로 자동 작성합니다.")
            if st.button("코멘터리 생성"):
                with st.spinner("Claude가 작성 중..."):
                    detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
                    commentary = generate_commentary(summary, detail_rows)
                st.text_area("LP 보고서용 코멘터리", commentary, height=300)

        with col2:
            st.markdown("#### 자연어 질문")
            st.caption("예: MOIC 2배 넘는 회사? / 바이오 섹터 현황? / IRR 가장 낮은 곳은?")
            question = st.text_input("질문 입력")
            if st.button("질문하기") and question:
                with st.spinner("답변 생성 중..."):
                    answer = answer_question(result_df, question)
                st.info(answer)

    # ── 포트폴리오사 뉴스 모니터링 ────────────────────
    st.markdown("---")
    st.markdown("### 포트폴리오사 뉴스 모니터링")
    st.caption("네이버 뉴스 API로 포트폴리오사 최신 기사를 실시간 검색 — 엑셀로는 불가능한 기능")

    _naver_id     = os.getenv("NAVER_CLIENT_ID")
    _naver_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not _naver_id:
        st.info("NAVER_CLIENT_ID가 .env에 없습니다.")
    elif "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        companies = st.session_state["result_df"]["회사명"].tolist()
        news_company = st.selectbox("기업 선택", ["전체 포트폴리오"] + companies, key="news_co")
        news_display = st.slider("기사 수", 3, 10, 5, key="news_n")

        if st.button("뉴스 검색", key="news_btn"):
            targets = companies if news_company == "전체 포트폴리오" else [news_company]
            all_news = {}

            headers = {
                "X-Naver-Client-Id": _naver_id,
                "X-Naver-Client-Secret": _naver_secret,
            }

            for corp in targets:
                try:
                    r = requests.get(
                        "https://openapi.naver.com/v1/search/news.json",
                        headers=headers,
                        params={"query": corp, "display": news_display, "sort": "date"},
                        timeout=8,
                    )
                    items = r.json().get("items", [])
                    if items:
                        all_news[corp] = items
                except Exception:
                    pass

            st.session_state["news_results"] = all_news

        if "news_results" in st.session_state and st.session_state["news_results"]:
            def _clean(text):
                return re.sub(r"<[^>]+>", "", text or "")

            for corp, items in st.session_state["news_results"].items():
                st.markdown(f"**{corp}** — {len(items)}건")
                for item in items:
                    title = _clean(item.get("title", ""))
                    desc  = _clean(item.get("description", ""))
                    date  = item.get("pubDate", "")[:16]
                    link  = item.get("link", "#")
                    st.markdown(f"""
<div style="border:1px solid #eae8e4;border-radius:10px;padding:14px 18px;margin-bottom:8px;background:#ffffff;">
  <a href="{link}" target="_blank" style="font-size:13px;font-weight:600;color:#1a1a1a;text-decoration:none;">{title}</a>
  <div style="font-size:12px;color:#999;margin-top:6px;line-height:1.5;">{desc[:120]}{"..." if len(desc)>120 else ""}</div>
  <div style="font-size:10px;color:#ccc;margin-top:6px;">{date}</div>
</div>
""", unsafe_allow_html=True)
                st.markdown("")
