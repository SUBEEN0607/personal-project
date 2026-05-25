import pandas as pd
from irr import xirr


def simulate_exit(
    invested: float,
    investment_date,
    exit_multiples: list[float],
    evaluation_date=None,
) -> pd.DataFrame:
    """Exit 배수별 MOIC·IRR·DPI 시뮬레이션"""
    if evaluation_date is None:
        evaluation_date = pd.Timestamp.today()

    inv_date = pd.to_datetime(investment_date)
    eval_date = pd.to_datetime(evaluation_date)

    rows = []
    for multiple in exit_multiples:
        exit_value = invested * multiple
        irr = xirr([(inv_date, -invested), (eval_date, exit_value)])
        rows.append({
            "Exit 배수": f"{multiple}x",
            "회수금액 (백만원)": int(exit_value),
            "MOIC": round(multiple, 2),
            "IRR (%)": irr,
            "DPI": round(multiple, 2),
        })

    return pd.DataFrame(rows)


def optimal_exit_timing(
    invested: float,
    current_value: float,
    investment_date,
    target_irr: float = 20.0,
) -> dict:
    """목표 IRR 달성을 위한 최소 회수 배수 계산"""
    inv_date = pd.to_datetime(investment_date)
    years = (pd.Timestamp.today() - inv_date).days / 365.25
    required_multiple = round((1 + target_irr / 100) ** years, 2)
    current_moic = round(current_value / invested, 2)

    return {
        "경과 연수": round(years, 1),
        f"IRR {target_irr}% 달성 최소 배수": required_multiple,
        "현재 MOIC": current_moic,
        "목표 달성 여부": "✅ 달성" if current_moic >= required_multiple else "❌ 미달",
    }
