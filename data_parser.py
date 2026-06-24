"""
데이터 입력 표준화 모듈
- 컬럼명 자동 매핑 (한글/영문/약어 대응)
- 단위 자동 감지 및 변환 (원/백만원/억원)
- 날짜 형식 자동 파싱
- 유효성 검증 + 오류 안내
"""
import pandas as pd
import re

# 컬럼명 자동 매핑 테이블
_COL_MAP = {
    "회사명": ["회사명", "company", "기업명", "투자처", "피투자사", "포트폴리오사", "name", "corp_name", "종목명"],
    "섹터": ["섹터", "sector", "업종", "산업", "분야", "industry", "투자분야"],
    "투자단계": ["투자단계", "stage", "라운드", "round", "투자라운드", "series", "단계"],
    "투자일": ["투자일", "투자일자", "invest_date", "investment_date", "투자실행일", "집행일"],
    "기준일": ["기준일", "평가일", "base_date", "valuation_date", "evaluation_date", "보고기준일"],
    "투자금액_백만원": ["투자금액_백만원", "투자금액", "투자원금", "investment", "invested", "inv_amount",
                      "투자금액(백만)", "투자금액(백만원)", "투자액", "출자금"],
    "현재가치_백만원": ["현재가치_백만원", "현재가치", "평가가치", "fair_value", "current_value", "fv",
                      "현재가치(백만)", "현재가치(백만원)", "평가액", "잔존가치"],
    "회수금액_백만원": ["회수금액_백만원", "회수금액", "회수액", "distribution", "realized", "회수",
                      "회수금액(백만)", "회수금액(백만원)", "배분금액", "분배금"],
    "지분율_%": ["지분율_%", "지분율", "stake", "ownership", "지분", "보유지분", "지분율(%)"],
}

# 필수 컬럼
_REQUIRED = ["회사명", "섹터", "투자단계", "투자일", "기준일", "투자금액_백만원", "회수금액_백만원"]
_OPTIONAL = ["현재가치_백만원", "지분율_%"]


def _find_best_match(col_name: str) -> str | None:
    col_lower = col_name.strip().lower().replace(" ", "").replace("_", "")
    for standard, variants in _COL_MAP.items():
        for v in variants:
            if col_lower == v.lower().replace(" ", "").replace("_", ""):
                return standard
    for standard, variants in _COL_MAP.items():
        for v in variants:
            if v.lower().replace(" ", "") in col_lower or col_lower in v.lower().replace(" ", ""):
                return standard
    return None


def _detect_unit(series: pd.Series) -> str:
    """숫자 컬럼의 단위 추정 (원/백만원/억원)"""
    vals = series.dropna()
    if len(vals) == 0:
        return "백만원"
    median = vals.median()
    if median > 1_000_000_000:
        return "원"
    elif median > 100_000:
        return "백만원"
    elif median > 100:
        return "억원"
    else:
        return "백만원"


def _convert_to_백만원(series: pd.Series, unit: str) -> pd.Series:
    if unit == "원":
        return series / 1_000_000
    elif unit == "억원":
        return series * 100
    return series


def standardize(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    입력 DataFrame을 표준 형식으로 변환.
    Returns: (표준화된 df, 경고 메시지 리스트)
    """
    warnings = []
    result = pd.DataFrame()

    # 1. 컬럼명 자동 매핑
    mapped = {}
    unmapped = []
    for col in df.columns:
        match = _find_best_match(col)
        if match:
            mapped[col] = match
        else:
            unmapped.append(col)

    if unmapped:
        warnings.append(f"매핑 안 된 컬럼 (무시됨): {', '.join(unmapped)}")

    df_renamed = df.rename(columns=mapped)

    # 2. 필수 컬럼 확인
    missing = [c for c in _REQUIRED if c not in df_renamed.columns]
    if missing:
        warnings.append(f"필수 컬럼 누락: {', '.join(missing)}")
        return df, warnings

    # 3. 선택 컬럼 기본값
    if "현재가치_백만원" not in df_renamed.columns:
        df_renamed["현재가치_백만원"] = 0
        warnings.append("현재가치 컬럼 없음 → 0으로 설정 (자동 밸류에이션 사용 가능)")
    if "지분율_%" not in df_renamed.columns:
        df_renamed["지분율_%"] = 10.0
        warnings.append("지분율 컬럼 없음 → 10%로 기본 설정")

    # 4. 숫자 컬럼 단위 자동 변환
    for col in ["투자금액_백만원", "현재가치_백만원", "회수금액_백만원"]:
        if col in df_renamed.columns:
            df_renamed[col] = pd.to_numeric(df_renamed[col], errors="coerce").fillna(0)
            unit = _detect_unit(df_renamed[col])
            if unit != "백만원":
                df_renamed[col] = _convert_to_백만원(df_renamed[col], unit)
                warnings.append(f"{col}: {unit} 단위 감지 → 백만원으로 자동 변환")

    # 5. 날짜 자동 파싱
    for col in ["투자일", "기준일"]:
        if col in df_renamed.columns:
            try:
                df_renamed[col] = pd.to_datetime(df_renamed[col], infer_datetime_format=True)
            except Exception:
                warnings.append(f"{col} 날짜 형식 인식 실패 — YYYY-MM-DD 형식으로 입력해주세요")

    # 6. 데이터 유효성 검증
    if (df_renamed["투자금액_백만원"] <= 0).any():
        bad = df_renamed[df_renamed["투자금액_백만원"] <= 0]["회사명"].tolist()
        warnings.append(f"투자금액 0 이하: {', '.join(str(x) for x in bad)}")

    if df_renamed["회사명"].duplicated().any():
        dups = df_renamed[df_renamed["회사명"].duplicated()]["회사명"].tolist()
        warnings.append(f"중복 회사명: {', '.join(str(x) for x in dups)}")

    # 표준 컬럼만 추출
    std_cols = _REQUIRED + _OPTIONAL
    available = [c for c in std_cols if c in df_renamed.columns]
    result = df_renamed[available].copy()

    return result, warnings
