import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display:flex; align-items:center; gap:16px; padding: 8px 0 20px 0; border-bottom: 2px solid #2e7d32; margin-bottom: 24px;">
  <div style="line-height:1;">
    <span style="font-family:'Georgia',serif; font-size:36px; font-weight:700; color:#2e7d32;">S</span><span style="font-family:'Georgia',serif; font-size:36px; font-weight:700; color:#1a1a1a;">DIC</span>
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
  <div style="display:flex; flex-wrap:wrap; gap:5px;">
    <span style="background:#f0faf0; border:1px solid #c8e6c9; color:#2e7d32; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:600;">DART</span>
    <span style="background:#e8f4fd; border:1px solid #b3d9f7; color:#1565c0; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:600;">ECOS</span>
    <span style="background:#fff8e1; border:1px solid #ffe082; color:#e65100; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:600;">KVIC</span>
    <span style="background:#f0faf0; border:1px solid #a5d6a7; color:#1b5e20; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:600;">NAVER</span>
    <span style="background:#fce4ec; border:1px solid #f48fb1; color:#880e4f; border-radius:4px; padding:3px 7px; font-size:10px; font-weight:600;">Claude</span>
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 대시보드", "📈 J-Curve", "🎯 시나리오 시뮬레이터",
    "📅 분기별 추이", "🏢 DART 조회", "💬 AI 분석", "🌐 거시지표",
])

# ── TAB 1: 대시보드 ──────────────────────────────
with tab1:
    if "result_df" not in st.session_state:
        st.info("사이드바에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        df = st.session_state["df"]
        summary = st.session_state["summary"]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("포트폴리오사 수", f"{summary['포트폴리오사 수']}개")
        c2.metric("펀드 MOIC", f"{summary['펀드 MOIC']}x")
        c3.metric("펀드 TVPI", f"{summary['펀드 TVPI']}x")
        c4.metric("펀드 DPI", f"{summary['펀드 DPI']}x")
        c5.metric("펀드 RVPI", f"{summary['펀드 RVPI']}x")
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                result_df.sort_values("MOIC", ascending=False),
                x="회사명", y="MOIC", color="섹터",
                title="포트폴리오사별 MOIC",
                labels={"MOIC": "MOIC (x)", "회사명": ""},
            )
            fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="1x")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            sector_df = df.groupby("섹터")["투자금액_백만원"].sum().reset_index()
            fig2 = px.pie(sector_df, names="섹터", values="투자금액_백만원", title="섹터별 투자 비중")
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.scatter(
            result_df, x="IRR(%)", y="MOIC",
            text="회사명", color="섹터", size="투자금액_백만원",
            title="MOIC vs IRR — 버블 크기: 투자금액",
        )
        fig3.update_traces(textposition="top center")
        fig3.add_hline(y=1.0, line_dash="dash", line_color="red")
        st.plotly_chart(fig3, use_container_width=True)

        st.divider()
        st.subheader("포트폴리오사별 지표")
        cols = ["회사명", "섹터", "투자단계", "투자금액_백만원", "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
        st.dataframe(result_df[cols], use_container_width=True)

        st.divider()
        if st.button("📄 PDF 보고서 생성"):
            with st.spinner("PDF 생성 중..."):
                detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
                commentary = generate_commentary(summary, detail_rows)
                pdf_bytes = generate_pdf(summary, result_df, commentary, quarter)
            st.download_button(
                "PDF 다운로드", pdf_bytes,
                file_name=f"portfolio_{quarter}.pdf",
                mime="application/pdf",
            )

# ── TAB 2: J-Curve ───────────────────────────────
with tab2:
    st.subheader("J-Curve 분석")
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
            line=dict(color="royalblue", width=2),
            fill="tozeroy", fillcolor="rgba(65,105,225,0.1)",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="손익분기")
        fig.update_layout(
            title="J-Curve — 펀드 누적 순현금흐름",
            xaxis_title="날짜", yaxis_title="누적 순현금흐름 (백만원)",
        )
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

# ── TAB 3: 시나리오 시뮬레이터 ──────────────────
with tab3:
    st.subheader("회수 시나리오 시뮬레이터")
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
            fig = px.bar(
                sim_df, x="Exit 배수", y="IRR (%)",
                color="IRR (%)", color_continuous_scale="RdYlGn",
                title=f"{company} — Exit 배수별 예상 IRR",
                text="IRR (%)",
            )
            fig.add_hline(y=20, line_dash="dash", line_color="blue", annotation_text="IRR 20%")
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
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

# ── TAB 4: 분기별 추이 ───────────────────────────
with tab4:
    st.subheader("분기별 추이")
    quarters = load_quarters()
    if not quarters:
        st.info("저장된 분기 데이터가 없습니다.\n\n데이터 로드 후 사이드바에서 [현재 데이터 저장]을 눌러 분기를 누적하세요.")
    else:
        trend_df = load_trend()
        fig = go.Figure()
        for metric in ["TVPI", "DPI", "RVPI"]:
            fig.add_trace(go.Scatter(
                x=trend_df["quarter"], y=trend_df[metric],
                mode="lines+markers", name=metric,
            ))
        fig.update_layout(title="분기별 펀드 지표 추이", xaxis_title="분기", yaxis_title="배수 (x)")
        st.plotly_chart(fig, use_container_width=True)
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

# ── TAB 5: DART 조회 ─────────────────────────────
with tab5:
    st.subheader("DART 기업 재무 조회")
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
            fig = px.bar(
                fin_df.melt(id_vars="연도", value_vars=["매출액", "영업이익", "당기순이익"]),
                x="연도", y="value", color="variable", barmode="group",
                title=f"{selected_name} 연도별 재무 현황",
                labels={"value": "금액 (원)", "variable": "항목"},
            )
            st.plotly_chart(fig, use_container_width=True)

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

# ── TAB 6: AI 분석 ───────────────────────────────
with tab6:
    st.subheader("AI 분석")
    if "result_df" not in st.session_state:
        st.info("먼저 대시보드에서 데이터를 로드하세요.")
    else:
        result_df = st.session_state["result_df"]
        summary = st.session_state["summary"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 분기 코멘터리")
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

# ── TAB 7: 거시지표 ──────────────────────────────
with tab7:
    st.subheader("거시지표 & VC 트렌드 벤치마크")

    # ECOS 섹션
    st.markdown("#### 한국은행 기준금리 & 환율 (ECOS)")
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
                              title="한국은행 기준금리 (%)", markers=True)
                fig.update_layout(xaxis_title="월", yaxis_title="금리 (%)")
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
                               title="원/달러 환율 월평균", markers=True)
                fig2.update_layout(xaxis_title="월", yaxis_title="환율 (원)")
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
    st.markdown("#### 🏦 한국벤처투자(KVIC) 모태펀드 시장 벤치마크")

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
                    color_continuous_scale="Blues",
                    title=f"{kvic_year}년 모태펀드 분야별 약정액",
                    labels={"총약정액(억원)": "약정액 (억원)", "투자분야": ""},
                )
                fig_s.update_layout(yaxis=dict(autorange="reversed"), height=420)
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
