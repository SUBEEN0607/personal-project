import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from calculator import load_portfolio, run_all, portfolio_summary
from commentary import generate_commentary
from rag import answer_question
from irr import j_curve_data
from simulator import simulate_exit, optimal_exit_timing
from db import save_snapshot, load_quarters, load_trend
from report import generate_pdf
from dart_client import search_company, get_financials

st.set_page_config(page_title="PE/VC 분기 보고 도우미", layout="wide")
st.title("PE/VC 분기 보고 도우미")

# ── 사이드바: 데이터 로드 & 저장 ─────────────────
with st.sidebar:
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

# 데이터 로드 처리
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 대시보드",
    "📈 J-Curve",
    "🎯 시나리오 시뮬레이터",
    "📅 분기별 추이",
    "🏢 DART 조회",
    "💬 AI 분석",
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
        fig.update_layout(
            title="분기별 펀드 지표 추이",
            xaxis_title="분기", yaxis_title="배수 (x)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(trend_df, use_container_width=True)

# ── TAB 5: DART 조회 ─────────────────────────────
with tab5:
    st.subheader("DART 기업 재무 조회")
    corp_name = st.text_input("기업명 입력 (예: 삼성전자, 카카오)")
    if st.button("검색") and corp_name:
        with st.spinner("DART에서 검색 중..."):
            results = search_company(corp_name)
        if results:
            options = {r["corp_name"]: r["corp_code"] for r in results}
            selected = st.selectbox("기업 선택", list(options.keys()))
            if st.button("재무제표 조회"):
                with st.spinner("재무제표 불러오는 중..."):
                    fin_df = get_financials(options[selected])
                if not fin_df.empty:
                    st.dataframe(fin_df, use_container_width=True)
                    fig = px.bar(
                        fin_df.melt(id_vars="연도", value_vars=["매출액", "영업이익", "당기순이익"]),
                        x="연도", y="value", color="variable", barmode="group",
                        title=f"{selected} 연도별 재무 현황",
                        labels={"value": "금액 (원)", "variable": "항목"},
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("재무 데이터를 불러올 수 없습니다.")
        else:
            st.warning("검색 결과가 없습니다.")

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
