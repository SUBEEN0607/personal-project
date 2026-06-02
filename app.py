import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64, os

from calculator import load_portfolio, run_all, portfolio_summary
from rag import answer_question
from irr import j_curve_data
from simulator import simulate_exit, optimal_exit_timing
from db import save_snapshot, load_quarters, load_trend
from report import (
    generate_pdf,
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

st.set_page_config(page_title="PE/VC 분기 보고 도우미", layout="wide")

# ── 표지/앱 전환 상태 ─────────────────────────────
if "show_cover" not in st.session_state:
    st.session_state["show_cover"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

html, body, [class*="css"], .stApp {
    font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
    background-color: #ffffff !important;
    color: #1a1a1a !important;
}
[data-testid="stAppViewContainer"] { background-color: #ffffff !important; }
[data-testid="stSidebar"] {
    background-color: #f2f2f2 !important;
    border-right: 1px solid #eeeeee !important;
    border-left: 3px solid #2e7d32 !important;
}
h1, h2, h3, h4, h5, h6 {
    color: #1a1a1a !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em !important;
}
.stMarkdown, .stText, label, .stDataFrame, .stAlert, .stSidebar, .stSidebar * {
    color: #1a1a1a !important;
}
.stTextInput > div > div > input {
    border: 1px solid #e0e0e0 !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
    font-size: 15px !important;
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2e7d32 !important;
    box-shadow: 0 0 0 3px rgba(46,125,50,0.15) !important;
}
[data-baseweb="input"]:focus-within {
    border-color: #2e7d32 !important;
    box-shadow: 0 0 0 3px rgba(46,125,50,0.15) !important;
}
.stButton > button {
    color: #2e7d32 !important;
    border: 1.5px solid #2e7d32 !important;
    background-color: #ffffff !important;
    border-radius: 6px !important;
    padding: 10px 28px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background-color: #2e7d32 !important;
    color: #ffffff !important;
}
[data-testid="stDataFrame"] thead th, [data-testid="stDataFrame"] th {
    background-color: #2e7d32 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    text-align: center !important;
    padding: 12px 16px !important;
    border: none !important;
}
[data-testid="stDataFrame"] tbody td, [data-testid="stDataFrame"] td {
    text-align: center !important;
    padding: 10px 16px !important;
    border-bottom: 1px solid #f0f0f0 !important;
    color: #1a1a1a !important;
    font-size: 14px !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td { background-color: #f9fafb !important; }
[data-testid="stDataFrame"] tbody tr:hover td { background-color: #e8f5e9 !important; }
hr { border: none !important; border-top: 1px solid #eeeeee !important; margin: 12px 0 !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e8e8e8 !important;
    border-radius: 12px !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08) !important;
    background: #ffffff !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 12px 32px rgba(46,125,50,0.15), 0 4px 10px rgba(0,0,0,0.08) !important;
}
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
[data-testid="stMetricLabel"] { font-size: 11px !important; color: #999 !important; letter-spacing: 0.07em; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #1a1a1a !important; letter-spacing: -0.03em; }
[data-testid="stMetricDelta"] { font-size: 13px !important; font-weight: 500 !important; }
[data-baseweb="tab-list"] { border-bottom: 2px solid #eeeeee !important; gap: 4px; }
[data-baseweb="tab"] {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #666 !important;
    padding: 10px 18px !important;
    border-radius: 6px 6px 0 0 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #2e7d32 !important;
    border-bottom: 2px solid #2e7d32 !important;
    background-color: #f1f8f1 !important;
}
[data-testid="stSelectbox"] > div > div {
    border: 1px solid #e0e0e0 !important;
    border-radius: 6px !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] [role="slider"] { color: #2e7d32 !important; }
[data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] { background-color: #2e7d32 !important; }
.stDownloadButton > button {
    background-color: #f1f8f1 !important;
    color: #2e7d32 !important;
    border: 1px solid #2e7d32 !important;
    border-radius: 6px !important;
}
.stDownloadButton > button:hover { background-color: #2e7d32 !important; color: #ffffff !important; }
[data-testid="stExpander"] { border: 1px solid #e8e8e8 !important; border-radius: 8px !important; }

/* 표지 시작하기 버튼 */
.cover-btn > button {
    background-color: rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
    border: 2px solid rgba(255,255,255,0.7) !important;
    border-radius: 30px !important;
    padding: 14px 40px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    backdrop-filter: blur(4px) !important;
    transition: all 0.25s ease !important;
}
.cover-btn > button:hover {
    background-color: rgba(255,255,255,0.30) !important;
    border-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ── 배경 이미지 base64 로드 ───────────────────────
_wp_path = os.path.join(os.path.dirname(__file__), "skku_wallpaper.jpg")
_wp_b64 = ""
if os.path.exists(_wp_path):
    with open(_wp_path, "rb") as _f:
        _wp_b64 = base64.b64encode(_f.read()).decode()

if st.session_state["show_cover"]:
    # ── 표지 페이지 ──────────────────────────────
    st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background:
        linear-gradient(160deg, rgba(180,210,160,0.85) 0%, rgba(30,60,35,0.92) 100%),
        url('data:image/jpeg;base64,{_wp_b64}') center 60%/cover no-repeat !important;
}}
[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="stMain"] * {{
    background-color: transparent !important;
    background: transparent !important;
}}
</style>
<div style="
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    min-height:72vh; text-align:center; padding: 60px 20px 40px 20px;
">
  <!-- 로고 -->
  <div style="line-height:1; margin-bottom:10px;">
    <span style="font-family:'Georgia',serif; font-size:72px; font-weight:700;
                 color:#ffffff; text-shadow:2px 3px 12px rgba(0,0,0,0.4);">S</span>
    <span style="font-family:'Georgia',serif; font-size:72px; font-weight:700;
                 color:#e8f5e9; text-shadow:2px 3px 12px rgba(0,0,0,0.4);">DIC</span>
  </div>
  <div style="font-size:13px; color:rgba(255,255,255,0.75); letter-spacing:0.18em;
              font-weight:500; margin-bottom:36px;">
    SKKU · Digital IT Consulting
  </div>

  <!-- 타이틀 -->
  <div style="font-size:42px; font-weight:700; color:#ffffff;
              letter-spacing:-0.02em; text-shadow:1px 2px 10px rgba(0,0,0,0.35);
              margin-bottom:12px; line-height:1.2;">
    PE/VC 분기 보고 도우미
  </div>
  <div style="font-size:15px; color:rgba(255,255,255,0.7); margin-bottom:48px;">
    이수빈 · SDIC 개인 프로젝트
  </div>

  <!-- API 배지 -->
  <div style="display:flex; gap:14px; flex-wrap:wrap; justify-content:center; margin-bottom:52px; align-items:center;">
    <svg title="DART" width="30" height="30" viewBox="0 0 22 22"><rect width="22" height="22" rx="5" fill="none"/><path d="M5 6h5.8c2.8 0 4.4 1.5 4.4 4s-1.6 4-4.4 4H7.2V17H5V6zm2.2 5.8h3.2c1.4 0 2.2-.7 2.2-1.8s-.8-1.8-2.2-1.8H7.2v3.6z" fill="white"/></svg>
    <svg title="ECOS (한국은행)" width="30" height="30" viewBox="0 0 22 22"><circle cx="11" cy="11" r="11" fill="none"/><text x="11" y="15.5" text-anchor="middle" fill="white" font-size="11" font-weight="700" font-family="serif">₩</text></svg>
    <svg title="KVIC" width="30" height="30" viewBox="0 0 22 22"><circle cx="11" cy="11" r="11" fill="none"/><path d="M6 6h2.3v4.2l3.8-4.2H14.8l-4.2 4.5 4.4 5.5h-2.8l-3.1-3.9-1 1.1V16H6z" fill="white"/></svg>
    <svg title="Naver" width="30" height="30" viewBox="0 0 22 22"><rect width="22" height="22" rx="5" fill="none"/><path d="M5.5 5.5h3.3l3.9 5.8V5.5h3V16.5h-3.2l-4-5.9v5.9h-3z" fill="white"/></svg>
    <span title="Claude AI" style="color:white;font-size:28px;line-height:1;display:inline-flex;align-items:center;justify-content:center;">✳</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # 시작하기 버튼 — 가운데 배치
    col_l, col_c, col_r = st.columns([2, 1, 2])
    with col_c:
        st.markdown('<div class="cover-btn">', unsafe_allow_html=True)
        if st.button("시작하기 →", use_container_width=True):
            st.session_state["show_cover"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# ── 일반 헤더: 표지 통과 후 ──────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:16px;
            padding: 8px 0 20px 0; border-bottom: 2px solid #2e7d32; margin-bottom: 24px;">
  <div style="line-height:1;">
    <span style="font-family:'Georgia',serif; font-size:36px; font-weight:700; color:#2e7d32;">S</span>
    <span style="font-family:'Georgia',serif; font-size:36px; font-weight:700; color:#1a1a1a;">DIC</span>
  </div>
  <div style="width:1px; height:40px; background:#ddd;"></div>
  <div>
    <div style="font-size:22px; font-weight:600; color:#1a1a1a; letter-spacing:-0.02em;">PE/VC 분기 보고 도우미</div>
    <div style="font-size:12px; color:#999; margin-top:2px;">이수빈 · SKKU Digital IT Consulting</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 사이드바: 표지 ───────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding: 20px 8px 12px 8px; border-bottom: 1px solid #e0e0e0; margin-bottom: 16px;">

  <!-- SDIC 로고 -->
  <div style="line-height:1; margin-bottom: 4px;">
    <span style="font-family: 'Georgia', serif; font-size: 42px; font-weight: 700; color: #2e7d32; letter-spacing:-1px;">S</span><span style="font-family: 'Georgia', serif; font-size: 42px; font-weight: 700; color: #1a1a1a; letter-spacing:-1px;">DIC</span>
  </div>
  <div style="font-size: 10px; color: #888; letter-spacing: 0.12em; font-weight: 500; margin-bottom: 14px;">SKKU · Digital IT Consulting</div>

  <!-- 프로젝트명 + 이름 -->
  <div style="font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 2px;">PE/VC 분기 보고 도우미</div>
  <div style="font-size: 11px; color: #999; margin-bottom: 16px;">이수빈 개인 프로젝트</div>

  <!-- API 배지 -->
  <div style="font-size: 10px; color: #aaa; letter-spacing:0.08em; margin-bottom: 8px; font-weight:500;">POWERED BY</div>
  <div style="display:flex; flex-wrap:wrap; gap:7px; align-items:center;">
    <svg title="DART" width="22" height="22" viewBox="0 0 22 22" style="flex-shrink:0;"><rect width="22" height="22" rx="5" fill="none"/><path d="M5 6h5.8c2.8 0 4.4 1.5 4.4 4s-1.6 4-4.4 4H7.2V17H5V6zm2.2 5.8h3.2c1.4 0 2.2-.7 2.2-1.8s-.8-1.8-2.2-1.8H7.2v3.6z" fill="#1a1a1a"/></svg>
    <svg title="ECOS (한국은행)" width="22" height="22" viewBox="0 0 22 22" style="flex-shrink:0;"><circle cx="11" cy="11" r="11" fill="none"/><text x="11" y="15.5" text-anchor="middle" fill="#1a1a1a" font-size="11" font-weight="700" font-family="serif">₩</text></svg>
    <svg title="KVIC" width="22" height="22" viewBox="0 0 22 22" style="flex-shrink:0;"><circle cx="11" cy="11" r="11" fill="none"/><path d="M6 6h2.3v4.2l3.8-4.2H14.8l-4.2 4.5 4.4 5.5h-2.8l-3.1-3.9-1 1.1V16H6z" fill="#1a1a1a"/></svg>
    <svg title="Naver" width="22" height="22" viewBox="0 0 22 22" style="flex-shrink:0;"><rect width="22" height="22" rx="5" fill="none"/><path d="M5.5 5.5h3.3l3.9 5.8V5.5h3V16.5h-3.2l-4-5.9v5.9h-3z" fill="#1a1a1a"/></svg>
    <span title="Claude AI" style="color:#1a1a1a;font-size:20px;line-height:1;display:inline-flex;align-items:center;justify-content:center;">✳</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.header("데이터 로드")
    uploaded = st.file_uploader("CSV 또는 Excel 업로드", type=["csv", "xlsx"])
    use_sample = st.button("샘플 데이터 불러오기")

    st.divider()
    st.header("분기 저장")
    quarter = st.text_input("분기 입력 (예: 2024Q1)", value="2024Q1")
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

# ── 탭 ───────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 대시보드", "📈 펀드 추이", "🎯 투자 분석", "🌐 시장 벤치마크", "💬 AI 분석",
])

# ── TAB 1: 대시보드 ──────────────────────────────
with tab1:
    if "result_df" not in st.session_state:
        st.info("사이드바에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        df = st.session_state["df"]
        summary = st.session_state["summary"]
        _GREEN = ["#1b5e20","#2e7d32","#388e3c","#43a047","#66bb6a","#81c784","#a5d6a7","#c8e6c9"]

        moic  = summary["펀드 MOIC"]
        tvpi  = summary["펀드 TVPI"]
        dpi   = summary["펀드 DPI"]
        rvpi  = summary["펀드 RVPI"]
        n     = summary["포트폴리오사 수"]
        avg_irr = round(result_df["IRR(%)"].mean(), 1)

        # 색상 기준: MOIC>=2 초록, 1~2 주황, <1 빨강
        def _moic_color(v):
            if v >= 2.0: return "#2e7d32"
            if v >= 1.0: return "#e65100"
            return "#c62828"
        def _irr_color(v):
            if v >= 15: return "#1565c0"
            if v >= 8:  return "#6a1b9a"
            return "#c62828"

        # ── Level 1: Hero 지표 (MOIC + IRR) ──────
        st.markdown(f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
  <div style="background:linear-gradient(135deg,#1b5e20,#2e7d32);border-radius:16px;padding:28px 32px;color:#fff;">
    <div style="font-size:10px;letter-spacing:0.12em;opacity:0.75;text-transform:uppercase;margin-bottom:6px;">펀드 MOIC · 핵심 수익 배수</div>
    <div style="font-size:56px;font-weight:700;letter-spacing:-0.03em;line-height:1;">{moic}x</div>
    <div style="font-size:12px;opacity:0.65;margin-top:8px;">투자원금 대비 전체 가치</div>
  </div>
  <div style="background:linear-gradient(135deg,#1b5e20,#388e3c);border-radius:16px;padding:28px 32px;color:#fff;">
    <div style="font-size:10px;letter-spacing:0.12em;opacity:0.75;text-transform:uppercase;margin-bottom:6px;">펀드 IRR · 내부수익률 (가중평균)</div>
    <div style="font-size:56px;font-weight:700;letter-spacing:-0.03em;line-height:1;">{avg_irr}%</div>
    <div style="font-size:12px;opacity:0.65;margin-top:8px;">시간 가치 반영 연환산 수익률</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Level 2: 보조 지표 (DPI·RVPI·TVPI·기업수) ──
        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px;">
  <div style="background:#f1f8f1;border:1.5px solid #a5d6a7;border-radius:12px;padding:18px 20px;">
    <div style="font-size:10px;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">DPI</div>
    <div style="font-size:28px;font-weight:700;color:#2e7d32;letter-spacing:-0.02em;">{dpi}x</div>
    <div style="font-size:11px;color:#999;margin-top:2px;">현금 회수율</div>
  </div>
  <div style="background:#f1f8f1;border:1.5px solid #a5d6a7;border-radius:12px;padding:18px 20px;">
    <div style="font-size:10px;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">RVPI</div>
    <div style="font-size:28px;font-weight:700;color:#2e7d32;letter-spacing:-0.02em;">{rvpi}x</div>
    <div style="font-size:11px;color:#999;margin-top:2px;">잔존 가치 배수</div>
  </div>
  <div style="background:#f1f8f1;border:1.5px solid #a5d6a7;border-radius:12px;padding:18px 20px;">
    <div style="font-size:10px;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">TVPI</div>
    <div style="font-size:28px;font-weight:700;color:#2e7d32;letter-spacing:-0.02em;">{tvpi}x</div>
    <div style="font-size:11px;color:#999;margin-top:2px;">총 가치 배수</div>
  </div>
  <div style="background:#fafafa;border:1.5px solid #e0e0e0;border-radius:12px;padding:18px 20px;">
    <div style="font-size:10px;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">포트폴리오사</div>
    <div style="font-size:28px;font-weight:700;color:#1a1a1a;letter-spacing:-0.02em;">{n}개</div>
    <div style="font-size:11px;color:#999;margin-top:2px;">투자 기업 수</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── 지표 용어 설명 ───────────────────────
        with st.expander("📖 지표 용어 설명"):
            st.markdown("""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px 24px;font-size:13.5px;line-height:1.7;color:#333;">
  <div>
    <span style="font-weight:700;color:#1b5e20;">MOIC</span> <span style="color:#999;font-size:11px;">Multiple on Invested Capital</span><br>
    투자 원금 대비 현재 총 가치 배수. <b>1x = 원금 회수</b>, 2x = 2배 수익.
    실현·미실현 모두 포함하며 시간 가치는 반영하지 않음.
  </div>
  <div>
    <span style="font-weight:700;color:#2e7d32;">IRR</span> <span style="color:#999;font-size:11px;">Internal Rate of Return</span><br>
    투자·회수 현금흐름의 시간 가치를 반영한 <b>연환산 수익률</b>.
    MOIC보다 보유 기간 불이익을 정확히 반영하여 펀드 성과의 핵심 지표로 활용.
  </div>
  <div>
    <span style="font-weight:700;color:#2e7d32;">DPI</span> <span style="color:#999;font-size:11px;">Distributions to Paid-In</span><br>
    LP 출자금 대비 <b>실제 현금 회수 배수</b>. 1x 이상이면 원금 이상 회수 완료.
    펀드 만기가 가까울수록 중요한 지표.
  </div>
  <div>
    <span style="font-weight:700;color:#2e7d32;">RVPI</span> <span style="color:#999;font-size:11px;">Residual Value to Paid-In</span><br>
    LP 출자금 대비 <b>아직 회수되지 않은 잔존 가치 배수</b>.
    포트폴리오사의 미실현 평가가치를 나타내며, 펀드 초기일수록 높게 나타남.
  </div>
  <div>
    <span style="font-weight:700;color:#2e7d32;">TVPI</span> <span style="color:#999;font-size:11px;">Total Value to Paid-In</span><br>
    <b>DPI + RVPI</b>. 실현·미실현 가치의 합산 배수로 MOIC와 유사.
    펀드 전체 성과를 종합적으로 나타내는 지표.
  </div>
  <div style="display:flex;align-items:flex-start;">
    <div>
      <span style="font-weight:700;color:#555;">IRR vs MOIC 관계</span><br>
      같은 MOIC라도 <b>보유 기간이 짧을수록 IRR이 높음</b>.
      예: 2x MOIC를 3년 만에 달성하면 IRR ≈ 26%, 5년이면 IRR ≈ 15%.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Level 3: 핵심 차트 — MOIC 전폭 ──────
        st.markdown("##### 포트폴리오사별 MOIC")
        fig = px.bar(
            result_df.sort_values("MOIC", ascending=False),
            x="회사명", y="MOIC", color="섹터",
            color_discrete_sequence=_GREEN,
            labels={"MOIC": "MOIC (x)", "회사명": ""},
        )
        fig.add_hline(y=1.0, line_dash="dash", line_color="#e53935", annotation_text="기준 1x")
        fig.update_layout(height=320, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # ── Level 4: 보조 차트 — 트리맵 + 버블 ──
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("##### 투자금액 & MOIC 분포")
            fig3 = px.treemap(
                result_df, path=["섹터","회사명"],
                values="투자금액_백만원", color="MOIC",
                color_continuous_scale=["#c8e6c9","#2e7d32","#1b5e20"],
                hover_data={"IRR(%)": True, "TVPI": True},
            )
            fig3.update_traces(textinfo="label+value", textfont_size=13)
            fig3.update_layout(margin=dict(t=10))
            st.plotly_chart(fig3, use_container_width=True)

        with col_b:
            st.markdown("##### MOIC vs IRR 산점도")
            max_size = result_df["투자금액_백만원"].max()
            fig4 = px.scatter(
                result_df, x="IRR(%)", y="MOIC",
                text="회사명", color="섹터", size="투자금액_백만원",
                color_discrete_sequence=_GREEN, size_max=70,
            )
            fig4.update_traces(
                textposition="top center",
                marker=dict(sizeref=2.0*max_size/(70**2), sizemode="area", opacity=0.8),
            )
            fig4.add_hline(y=1.0, line_dash="dash", line_color="#e53935", annotation_text="MOIC 1x")
            fig4.add_vline(x=0, line_dash="dash", line_color="#bbb")
            fig4.update_layout(margin=dict(t=10))
            st.plotly_chart(fig4, use_container_width=True)

        # ── Level 5: 섹터 파이 + 상세 테이블 ──
        st.markdown("---")
        col_p, col_t = st.columns([1, 2])
        with col_p:
            st.markdown("##### 섹터별 투자 비중")
            sector_df = df.groupby("섹터")["투자금액_백만원"].sum().reset_index()
            fig2 = px.pie(sector_df, names="섹터", values="투자금액_백만원",
                          color_discrete_sequence=_GREEN)
            fig2.update_traces(textinfo="label+percent", hole=0.35)
            fig2.update_layout(margin=dict(t=10, b=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        with col_t:
            st.markdown("##### 포트폴리오사별 상세 지표")
            cols = ["회사명","섹터","투자단계","투자금액_백만원","MOIC","IRR(%)","DPI","RVPI","TVPI"]
            st.dataframe(result_df[cols], use_container_width=True, height=280)

        st.markdown("---")
        if st.button("📄 PDF 보고서 생성"):
            with st.spinner("PDF 생성 중..."):
                detail_rows = result_df[["회사명","MOIC","IRR(%)","TVPI"]].to_dict("records")
                commentary = generate_commentary(summary, detail_rows)
                pdf_bytes = generate_pdf(summary, result_df, commentary, quarter)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"portfolio_{quarter}.pdf",
                mime="application/pdf",
            )

# ── TAB 2: 펀드 추이 (J-Curve + 분기별 추이) ────
with tab2:
    # ── J-Curve 섹션 ──────────────────────────────
    st.markdown("""
<div style="background:#f1f8f1;border-left:4px solid #2e7d32;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:15px;font-weight:600;color:#1b5e20;margin-bottom:6px;">📈 J-Curve란?</div>
  <div style="font-size:14px;color:#444;line-height:1.6;">
    사모펀드·VC 펀드는 초기에 투자 집행과 운용 비용으로 <b>누적 현금흐름이 마이너스(−)</b>로 진입합니다.
    이후 포트폴리오사의 가치가 성장해 회수가 이뤄지면 플러스(+)로 전환되는데,
    이 흐름이 알파벳 <b>'J'자 형태</b>를 그려 <em>J-Curve</em>라고 부릅니다.
    손익분기 시점(Break-even)과 회수 속도를 파악하는 데 활용합니다.
  </div>
</div>
""", unsafe_allow_html=True)

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
            line=dict(color="#2e7d32", width=2.5),
            fill="tozeroy", fillcolor="rgba(46,125,50,0.12)",
            marker=dict(color="#2e7d32", size=7),
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="#c62828",
                      annotation_text="손익분기(Break-even)",
                      annotation_font_color="#c62828")
        fig.update_layout(
            title="J-Curve — 펀드 누적 순현금흐름",
            xaxis_title="날짜", yaxis_title="누적 순현금흐름 (백만원)",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#1a1a1a",
        )
        fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("컬럼: 회사명, 날짜(YYYY-MM-DD), 현금흐름_백만원 — 투자=음수, 배당·회수=양수")

        st.divider()
        if st.button("📄 J-Curve 보고서 생성 (AI 해석 포함)", key="jcurve_pdf"):
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
    st.markdown("### 📅 분기별 펀드 지표 추이")
    quarters = load_quarters()
    if not quarters:
        st.info("저장된 분기 데이터가 없습니다.\n\n데이터 로드 후 사이드바에서 [현재 데이터 저장]을 눌러 분기를 누적하세요.")
    else:
        trend_df = load_trend()
        _LINE_COLORS = {"TVPI": "#1b5e20", "DPI": "#43a047", "RVPI": "#81c784"}
        fig_q = go.Figure()
        for metric in ["TVPI", "DPI", "RVPI"]:
            fig_q.add_trace(go.Scatter(
                x=trend_df["quarter"], y=trend_df[metric],
                mode="lines+markers", name=metric,
                line=dict(color=_LINE_COLORS[metric], width=2),
                marker=dict(color=_LINE_COLORS[metric], size=8),
            ))
        fig_q.update_layout(
            title="분기별 펀드 지표 추이 (TVPI · DPI · RVPI)",
            xaxis_title="분기", yaxis_title="배수 (x)",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
        )
        fig_q.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
        fig_q.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(trend_df, use_container_width=True)

        st.divider()
        if st.button("📄 분기 추이 보고서 생성 (AI 해석 포함)", key="trend_pdf"):
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_quarterly_trend(trend_df)
                pdf_bytes = generate_quarterly_pdf(trend_df, ai_text, quarter)
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"quarterly_trend_{quarter or 'report'}.pdf",
                mime="application/pdf",
            )

# ── TAB 3: 투자 분석 (시나리오 + DART) ──────────
with tab3:
    # ── 시나리오 시뮬레이터 섹션 ───────────────────
    st.markdown("### 🎯 회수 시나리오 시뮬레이터")
    if "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        df = st.session_state["df"]

        company = st.selectbox("포트폴리오사 선택", result_df["회사명"].tolist())
        r = result_df[result_df["회사명"] == company].iloc[0]
        raw_r = df[df["회사명"] == company].iloc[0]

        left, right = st.columns([1, 2])
        with left:
            st.metric("투자금액", f"{int(raw_r['투자금액_백만원']):,}백만원")
            st.metric("현재 MOIC", f"{r['MOIC']}x")
            st.metric("현재 IRR (XIRR)", f"{r['IRR(%)']}%")
            target_irr = st.slider("목표 IRR (%)", 10, 40, 20)
            opt = optimal_exit_timing(
                raw_r["투자금액_백만원"], raw_r["현재가치_백만원"],
                raw_r["투자일"], target_irr,
            )
            st.info(
                f"목표 IRR {target_irr}% 달성 최소 배수: **{opt[f'IRR {target_irr}% 달성 최소 배수']}x**\n\n"
                f"{opt['목표 달성 여부']}"
            )

        with right:
            sim_df = simulate_exit(
                raw_r["투자금액_백만원"], raw_r["투자일"],
                [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
            )
            fig_sim = px.bar(
                sim_df, x="Exit 배수", y="IRR (%)",
                color="IRR (%)", color_continuous_scale="Greens",
                title=f"{company} — Exit 배수별 예상 IRR",
                text="IRR (%)",
            )
            fig_sim.add_hline(
                y=target_irr, line_dash="dash", line_color="#2e7d32",
                annotation_text=f"목표 IRR {target_irr}%",
                annotation_font_color="#2e7d32",
            )
            fig_sim.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_sim.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
            )
            st.plotly_chart(fig_sim, use_container_width=True)
            st.dataframe(sim_df, use_container_width=True)

        st.divider()
        if st.button("📄 시나리오 보고서 생성 (AI 해석 포함)", key="sim_pdf"):
            opt_result = optimal_exit_timing(
                raw_r["투자금액_백만원"], raw_r["현재가치_백만원"],
                raw_r["투자일"], target_irr,
            )
            full_sim = simulate_exit(
                raw_r["투자금액_백만원"], raw_r["투자일"],
                [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
            )
            with st.spinner("AI 해석 생성 중..."):
                ai_text = interpret_scenario(company, full_sim, opt_result)
                pdf_bytes = generate_scenario_pdf(company, full_sim, opt_result, ai_text, quarter)
            st.text_area("AI 해석 미리보기", ai_text, height=200)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"scenario_{company}_{quarter or 'report'}.pdf",
                mime="application/pdf",
            )

    # ── DART 재무 조회 섹션 ─────────────────────────
    st.markdown("---")
    st.markdown("### 🏢 DART 기업 재무 조회")
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
                color_discrete_sequence=["#2e7d32", "#66bb6a", "#a5d6a7"],
                title=f"{selected_name} 연도별 재무 현황",
                labels={"value": "금액 (원)", "variable": "항목"},
            )
            fig_dart.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
            )
            st.plotly_chart(fig_dart, use_container_width=True)

            st.divider()
            if st.button("📄 DART 재무분석 보고서 생성 (AI 해석 포함)", key="dart_pdf"):
                with st.spinner("AI 해석 생성 중..."):
                    ai_text = interpret_dart_financials(selected_name, fin_df)
                    pdf_bytes = generate_dart_pdf(selected_name, fin_df, ai_text, quarter)
                st.text_area("AI 해석 미리보기", ai_text, height=200)
                st.download_button(
                    "PDF 다운로드", pdf_bytes,
                    file_name=f"dart_{selected_name}_{quarter or 'report'}.pdf",
                    mime="application/pdf",
                )

    # ── Waterfall 계산기 섹션 ───────────────────────
    st.markdown("---")
    st.markdown("### 💧 Waterfall 분배 계산기")
    st.markdown("""
<div style="background:#f1f8f1;border-left:4px solid #2e7d32;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:15px;font-weight:600;color:#1b5e20;margin-bottom:6px;">Waterfall이란?</div>
  <div style="font-size:13.5px;color:#444;line-height:1.7;">
    PE 펀드 회수금을 <b>LP → GP 순서로 단계별 분배</b>하는 구조입니다.
    ① <b>원금 반환</b> → ② <b>Hurdle Rate 우선수익</b>(LP 독식) → ③ <b>GP 캐치업</b>(GP가 Carry 몫 확보) → ④ <b>초과수익 분배</b>(Carried Interest).
    GP는 Hurdle을 넘어야만 Carry를 받을 수 있어, LP 이익 보호 장치로 작동합니다.
  </div>
</div>
""", unsafe_allow_html=True)

    wf_c1, wf_c2, wf_c3 = st.columns(3)
    with wf_c1:
        wf_invested   = st.number_input("총 투자금액 (백만원)", min_value=100, value=10000, step=100, key="wf_inv")
        wf_proceeds   = st.number_input("총 회수금액 (백만원)", min_value=100, value=18000, step=100, key="wf_proc")
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
            marker_color="#2e7d32", text=wf_chart_df["LP"].apply(lambda x: f"{x:,.0f}"),
            textposition="inside", insidetextanchor="middle",
        ))
        fig_wf.add_trace(go.Bar(
            name="GP", x=wf_chart_df["단계"], y=wf_chart_df["GP"],
            marker_color="#81c784", text=wf_chart_df["GP"].apply(lambda x: f"{x:,.0f}" if x>0 else ""),
            textposition="inside", insidetextanchor="middle",
        ))
        fig_wf.update_layout(
            barmode="stack", height=340,
            title=f"단계별 LP/GP 분배 (총 회수금 {wf_proceeds:,}백만원)",
            yaxis_title="금액 (백만원)",
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#1a1a1a",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=50, b=10),
        )
        fig_wf.update_xaxes(showgrid=False)
        fig_wf.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
        st.plotly_chart(fig_wf, use_container_width=True)

        # LP vs GP 최종 파이
        col_pie, col_txt = st.columns([1, 1])
        with col_pie:
            fig_pie = px.pie(
                values=[total_lp, total_gp],
                names=["LP", "GP"],
                color_discrete_sequence=["#2e7d32", "#a5d6a7"],
                title="최종 LP / GP 분배 비율",
                hole=0.4,
            )
            fig_pie.update_traces(textinfo="label+percent+value",
                                  texttemplate="%{label}<br>%{percent}<br>%{value:,.0f}백만원")
            fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=0),
                                  paper_bgcolor="#ffffff", font_color="#1a1a1a")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_txt:
            st.markdown(f"""
<div style="padding:16px 0;font-size:13.5px;line-height:2;color:#333;">
  <div><b>총 수익</b>: {total_profit:,.0f}백만원</div>
  <div><b>LP 수익</b>: {total_lp-wf_invested:,.0f}백만원
    <span style="color:#2e7d32;font-size:12px;"> (원금 제외 순수익)</span></div>
  <div><b>GP Carry</b>: {total_gp:,.0f}백만원
    <span style="color:#666;font-size:12px;"> (수익의 {eff_carry:.1f}%)</span></div>
  <div style="margin-top:12px;padding:10px 14px;background:#f1f8f1;border-radius:8px;">
    <b>LP MOIC</b>: {total_lp/wf_invested:.2f}x &nbsp;|&nbsp;
    <b>GP 실효 Carry</b>: {eff_carry:.1f}%
  </div>
  <div style="margin-top:8px;font-size:12px;color:#999;">
    Hurdle {wf_hurdle}% · 캐치업 {wf_catchup}% · Carry {wf_carry}% · {wf_years}년
  </div>
</div>
""", unsafe_allow_html=True)

# ── TAB 4: 시장 벤치마크 (거시지표 + KVIC) ──────
with tab4:
    st.markdown("### 🌐 거시지표 — 기준금리 & 환율 (ECOS)")

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
        if st.button("📄 거시지표 보고서 생성 (AI 해석 포함)", key="macro_pdf"):
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
    st.markdown("### 🏦 한국벤처투자(KVIC) 모태펀드 벤치마크")

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

# ── TAB 5: AI 분석 ────────────────────────────────
with tab5:
    st.markdown("### 💬 AI 분석")
    if "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        summary = st.session_state["summary"]

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
