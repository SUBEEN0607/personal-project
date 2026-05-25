import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_commentary(summary: dict, detail_rows: list[dict]) -> str:
    """펀드 요약 및 포트폴리오 데이터를 바탕으로 분기 코멘터리 생성"""

    portfolio_text = "\n".join(
        f"- {r['회사명']}: MOIC {r['MOIC']}x, IRR {r['IRR(%)']}%, TVPI {r['TVPI']}x"
        for r in detail_rows
    )

    prompt = f"""당신은 PE/VC 운용사의 분기 보고서를 작성하는 전문가입니다.
아래 펀드 성과 데이터를 바탕으로 LP 보고서용 한국어 코멘터리를 작성해주세요.

[펀드 요약]
- 포트폴리오사 수: {summary['포트폴리오사 수']}개
- 총 투자금액: {summary['총 투자금액 (백만원)']:,}백만원
- 펀드 MOIC: {summary['펀드 MOIC']}x
- 펀드 TVPI: {summary['펀드 TVPI']}x
- 펀드 DPI: {summary['펀드 DPI']}x
- 펀드 RVPI: {summary['펀드 RVPI']}x

[포트폴리오사별 주요 지표]
{portfolio_text}

작성 조건:
1. 3~4문단, 각 문단 3~4문장
2. 이번 분기 전체 성과 평가 → 주목할 포트폴리오사 언급 → 리스크 및 향후 전망 순서
3. 숫자는 반드시 포함, LP가 바로 활용할 수 있는 수준으로 작성
4. 전문적이고 간결한 한국어 사용"""

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


if __name__ == "__main__":
    from calculator import load_portfolio, run_all, portfolio_summary

    df = load_portfolio("sample_portfolio.csv")
    result_df = run_all(df)
    summary = portfolio_summary(df)

    detail_rows = result_df[["회사명", "MOIC", "IRR(%)", "TVPI"]].to_dict("records")
    commentary = generate_commentary(summary, detail_rows)

    print("=== Claude 코멘터리 ===")
    print(commentary)
