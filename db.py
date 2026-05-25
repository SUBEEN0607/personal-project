import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "portfolio.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            quarter     TEXT,
            saved_at    TEXT,
            company     TEXT,
            sector      TEXT,
            stage       TEXT,
            invested    REAL,
            current_val REAL,
            realized    REAL,
            moic        REAL,
            irr         REAL,
            dpi         REAL,
            rvpi        REAL,
            tvpi        REAL
        )
    """)
    conn.commit()
    return conn


def save_snapshot(result_df: pd.DataFrame, quarter: str):
    """분기 스냅샷 저장 (같은 분기면 덮어쓰기)"""
    conn = _get_conn()
    conn.execute("DELETE FROM snapshots WHERE quarter = ?", (quarter,))
    now = datetime.now().isoformat()
    for _, row in result_df.iterrows():
        conn.execute(
            "INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                quarter, now,
                row["회사명"], row["섹터"], row["투자단계"],
                row["투자금액_백만원"], row["현재가치_백만원"], row["회수금액_백만원"],
                row["MOIC"], row["IRR(%)"], row["DPI"], row["RVPI"], row["TVPI"],
            ),
        )
    conn.commit()
    conn.close()


def load_quarters() -> list[str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT quarter FROM snapshots ORDER BY quarter"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def load_trend() -> pd.DataFrame:
    """분기별 펀드 레벨 지표 추이"""
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM snapshots ORDER BY quarter", conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    trend = (
        df.groupby("quarter")
        .apply(lambda g: pd.Series({
            "TVPI": round((g["current_val"].sum() + g["realized"].sum()) / g["invested"].sum(), 2),
            "DPI":  round(g["realized"].sum() / g["invested"].sum(), 2),
            "RVPI": round(g["current_val"].sum() / g["invested"].sum(), 2),
            "총투자금액 (백만원)": int(g["invested"].sum()),
            "포트폴리오사 수": len(g),
        }))
        .reset_index()
    )
    return trend
