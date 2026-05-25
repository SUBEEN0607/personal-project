import pandas as pd


def load_portfolio(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["투자일"] = pd.to_datetime(df["투자일"])
    df["기준일"] = pd.to_datetime(df["기준일"])
    return df


def calculate_moic(row: pd.Series) -> float:
    total = row["현재가치_백만원"] + row["회수금액_백만원"]
    return round(total / row["투자금액_백만원"], 2)


def calculate_irr(row: pd.Series) -> float:
    """단순 2-현금흐름 IRR: (총가치/투자금)^(1/연수) - 1"""
    years = (row["기준일"] - row["투자일"]).days / 365.25
    if years <= 0:
        return 0.0
    total = row["현재가치_백만원"] + row["회수금액_백만원"]
    if total <= 0:
        return -100.0
    irr = (total / row["투자금액_백만원"]) ** (1 / years) - 1
    return round(irr * 100, 2)


def calculate_dpi(row: pd.Series) -> float:
    return round(row["회수금액_백만원"] / row["투자금액_백만원"], 2)


def calculate_rvpi(row: pd.Series) -> float:
    return round(row["현재가치_백만원"] / row["투자금액_백만원"], 2)


def calculate_tvpi(row: pd.Series) -> float:
    return round(calculate_dpi(row) + calculate_rvpi(row), 2)


def run_all(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MOIC"] = df.apply(calculate_moic, axis=1)
    df["IRR(%)"] = df.apply(calculate_irr, axis=1)
    df["DPI"] = df.apply(calculate_dpi, axis=1)
    df["RVPI"] = df.apply(calculate_rvpi, axis=1)
    df["TVPI"] = df.apply(calculate_tvpi, axis=1)
    return df


def portfolio_summary(df: pd.DataFrame) -> dict:
    total_invested = df["투자금액_백만원"].sum()
    total_current = df["현재가치_백만원"].sum()
    total_realized = df["회수금액_백만원"].sum()
    total_value = total_current + total_realized

    return {
        "포트폴리오사 수": len(df),
        "총 투자금액 (백만원)": int(total_invested),
        "현재가치 합계 (백만원)": int(total_current),
        "회수금액 합계 (백만원)": int(total_realized),
        "펀드 MOIC": round(total_value / total_invested, 2),
        "펀드 DPI": round(total_realized / total_invested, 2),
        "펀드 RVPI": round(total_current / total_invested, 2),
        "펀드 TVPI": round(total_value / total_invested, 2),
    }


if __name__ == "__main__":
    df = load_portfolio("sample_portfolio.csv")
    result_df = run_all(df)

    print("=== 펀드 요약 ===")
    for k, v in portfolio_summary(df).items():
        print(f"  {k}: {v}")

    print("\n=== 포트폴리오사별 지표 ===")
    cols = ["회사명", "MOIC", "IRR(%)", "DPI", "RVPI", "TVPI"]
    print(result_df[cols].to_string(index=False))
