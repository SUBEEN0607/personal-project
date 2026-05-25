import streamlit as st
import pandas as pd
from calculator import load_portfolio, run_all, portfolio_summary
from commentary import generate_commentary

st.set_page_config(page_title="PE/VC 분기 보고 도우미", layout="wide")
st.title("PE/VC 분기 보고 도우미")

uploaded = st.file_uploader("포트폴리오 CSV 파일 업로드", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    df["투자일"] = pd.to_datetime(df["투자일"])
    df["기준일"] = pd.to_datetime(df["기준일"])

    result_df = run_all(df)
    summary = portfolio_summary(df)

    # 펀드 요약 카드
    st.subheader("펀드 요약")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("포트폴리오사 수", f"{summary['포트폴리오사 수']}개")
    col2.metric("펀드 MOIC", f"{summary['펀드 MOIC']}x")
    col3.metric("펀드 TVPI", f"{summary['펀드 TVPI']}x")
    col4.metric("펀드 DPI", f"{summary['펀드 DPI']}x")
    col5.metric("펀드 RVPI", f"{summary['펀드 RVPI']}x")

    # 포트폴리오사별 지표 테이블
    st.subheader("포트폴리오사별 지표")
    display_cols = ["회사명", "섹터", "투자단계", "투자금액_백만원", "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
    st.dataframe(result_df[display_cols], use_container_width=True)

    # Claude 코멘터리
    st.subheader("AI 코멘터리")
    if st.button("코멘터리 생성"):
        with st.spinner("Claude가 코멘터리를 작성 중입니다..."):
            detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
            commentary = generate_commentary(summary, detail_rows)
        st.text_area("분기 코멘터리", commentary, height=300)
else:
    st.info("CSV 파일을 업로드하면 지표 계산과 AI 코멘터리가 자동 생성됩니다.")
    st.caption("샘플 파일: sample_portfolio.csv (컬럼: 회사명, 섹터, 투자단계, 투자일, 기준일, 투자금액_백만원, 현재가치_백만원, 회수금액_백만원)")
