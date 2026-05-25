import streamlit as st
import pandas as pd
import plotly.express as px
from calculator import load_portfolio, run_all, portfolio_summary
from commentary import generate_commentary
from rag import answer_question

st.set_page_config(page_title="PE/VC 분기 보고 도우미", layout="wide")
st.title("PE/VC 분기 보고 도우미")

# 데이터 로드 — 업로드 또는 샘플
upload_col, sample_col = st.columns([3, 1])
with upload_col:
    uploaded = st.file_uploader("포트폴리오 CSV 파일 업로드", type="csv")
with sample_col:
    st.write("")
    st.write("")
    use_sample = st.button("샘플 데이터 불러오기")

df = None
if uploaded:
    df = pd.read_csv(uploaded)
    df["투자일"] = pd.to_datetime(df["투자일"])
    df["기준일"] = pd.to_datetime(df["기준일"])
elif use_sample:
    df = load_portfolio("sample_portfolio.csv")
    st.success("샘플 데이터(8개사)를 불러왔습니다.")

if df is not None:
    result_df = run_all(df)
    summary = portfolio_summary(df)

    # 펀드 요약 카드
    st.subheader("펀드 요약")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("포트폴리오사 수", f"{summary['포트폴리오사 수']}개")
    c2.metric("펀드 MOIC", f"{summary['펀드 MOIC']}x")
    c3.metric("펀드 TVPI", f"{summary['펀드 TVPI']}x")
    c4.metric("펀드 DPI", f"{summary['펀드 DPI']}x")
    c5.metric("펀드 RVPI", f"{summary['펀드 RVPI']}x")

    st.divider()

    # 차트
    st.subheader("포트폴리오 시각화")
    chart1, chart2 = st.columns(2)

    with chart1:
        fig_moic = px.bar(
            result_df.sort_values("MOIC", ascending=False),
            x="회사명", y="MOIC", color="섹터",
            title="포트폴리오사별 MOIC",
            labels={"MOIC": "MOIC (x)", "회사명": ""},
        )
        fig_moic.add_hline(y=1.0, line_dash="dash", line_color="red",
                           annotation_text="원금 회수선(1x)")
        st.plotly_chart(fig_moic, use_container_width=True)

    with chart2:
        sector_df = df.groupby("섹터")["투자금액_백만원"].sum().reset_index()
        fig_sector = px.pie(
            sector_df, names="섹터", values="투자금액_백만원",
            title="섹터별 투자 비중",
        )
        st.plotly_chart(fig_sector, use_container_width=True)

    fig_scatter = px.scatter(
        result_df, x="IRR(%)", y="MOIC",
        text="회사명", color="섹터", size="투자금액_백만원",
        title="MOIC vs IRR — 버블 크기: 투자금액",
        labels={"IRR(%)": "IRR (%)", "MOIC": "MOIC (x)"},
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.add_hline(y=1.0, line_dash="dash", line_color="red")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # 포트폴리오 테이블
    st.subheader("포트폴리오사별 지표")
    display_cols = ["회사명", "섹터", "투자단계", "투자금액_백만원",
                    "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
    st.dataframe(result_df[display_cols], use_container_width=True)

    st.divider()

    # AI 코멘터리
    st.subheader("AI 코멘터리 생성")
    if st.button("코멘터리 생성"):
        with st.spinner("Claude가 코멘터리를 작성 중입니다..."):
            detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
            commentary = generate_commentary(summary, detail_rows)
        st.text_area("분기 코멘터리 (LP 보고서용)", commentary, height=300)

    st.divider()

    # 자연어 Q&A
    st.subheader("포트폴리오 질문하기")
    st.caption("예: MOIC 2배 넘는 회사 어디야? / IRR이 가장 낮은 회사는? / 바이오 섹터 투자 현황은?")
    question = st.text_input("질문 입력")
    if st.button("질문하기") and question:
        with st.spinner("답변 생성 중..."):
            answer = answer_question(result_df, question)
        st.info(answer)

else:
    st.info("CSV 파일을 업로드하거나 [샘플 데이터 불러오기] 버튼을 눌러주세요.")
    st.caption("필요 컬럼: 회사명, 섹터, 투자단계, 투자일, 기준일, 투자금액_백만원, 현재가치_백만원, 회수금액_백만원")
