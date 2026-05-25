import pandas as pd
from scipy.optimize import brentq


def xirr(cashflows: list[tuple]) -> float:
    """날짜 가중 XIRR. cashflows: [(date, amount), ...]
    투자금액은 음수, 회수·현재가치는 양수로 전달"""
    if len(cashflows) < 2:
        return 0.0

    dates = [pd.to_datetime(cf[0]) for cf in cashflows]
    amounts = [float(cf[1]) for cf in cashflows]
    t0 = min(dates)
    years = [(d - t0).days / 365.25 for d in dates]

    def npv(rate):
        return sum(a / (1 + rate) ** t for a, t in zip(amounts, years))

    try:
        result = brentq(npv, -0.9999, 100.0, maxiter=1000)
        return round(result * 100, 2)
    except Exception:
        total = sum(a for a in amounts if a > 0)
        invested = abs(sum(a for a in amounts if a < 0))
        total_years = max(years)
        if invested <= 0 or total_years <= 0 or total <= 0:
            return 0.0
        return round(((total / invested) ** (1 / total_years) - 1) * 100, 2)


def build_cashflows_from_row(row: pd.Series) -> list[tuple]:
    """portfolio row → 2~3 포인트 현금흐름 리스트"""
    cfs = [(row["투자일"], -row["투자금액_백만원"])]
    if row["회수금액_백만원"] > 0:
        mid = row["투자일"] + (row["기준일"] - row["투자일"]) / 2
        cfs.append((mid, row["회수금액_백만원"]))
    cfs.append((row["기준일"], row["현재가치_백만원"]))
    return cfs


def j_curve_data(cashflows_df: pd.DataFrame) -> pd.DataFrame:
    """펀드 전체 J-Curve용 누적 순현금흐름 시계열"""
    df = cashflows_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"])
    df = df.sort_values("날짜")
    fund = df.groupby("날짜")["현금흐름_백만원"].sum().reset_index()
    fund["누적현금흐름"] = fund["현금흐름_백만원"].cumsum()
    return fund
