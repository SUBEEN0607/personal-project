# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **🇰🇷 필수: 이 프로젝트의 모든 응답과 설명은 반드시 한국어로 해주세요.**
> 코드 변수명·함수명은 영어 snake_case, UI 텍스트와 모든 설명은 한국어.

---

## 자주 쓰는 명령어

```bash
# 패키지 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py

# data.py 단독 테스트 (재무 데이터 출력 확인)
python data.py
```

---

## 프로젝트 목적

DART API로 상장 기업 재무 데이터를 수집하고, LangGraph + Claude API로 자동 분석 리포트를 생성하는 개인 프로젝트.

---

## 프로젝트 구조

**데이터 흐름:**
```
기업명 입력 (app.py)
  → LangGraph Supervisor (graph.py)
    → Data Agent (data.py): DART-FSS API → SQLite
    → Report Agent (report.py): RAG + Claude API → PDF
  → 결과 출력 (app.py)
```

**파일별 역할:**
- `app.py` — Streamlit UI
- `graph.py` — LangGraph Supervisor 파이프라인
- `data.py` — DART API + SQLite + Text2SQL
- `report.py` — RAG 인덱스 + fpdf2 PDF 생성

---

## 파일 간 인터페이스 계약

`data.py`의 `get_financials(company: str) -> dict` 반환 구조:
```python
{
    2022: {"매출액": int, "영업이익": int, "순이익": int},  # 단위: 백만 원
    2023: {...},
    2024: {...},
}
# 기업명이 없으면 빈 dict {} 반환
```

`graph.py`의 `AnalysisState` 공유 상태:
```python
class AnalysisState(TypedDict):
    company: str       # 기업명
    corp_code: str     # DART 기업 코드
    financials: list   # 재무 데이터
    report: str        # 생성된 리포트 텍스트
```

---

## 기술 스택

- Python 3.11, LangGraph, Claude API (claude-haiku-4-5)
- DART-FSS API, OpenAI Embeddings, NumPy (코사인 유사도)
- SQLite, fpdf2, Streamlit

## 환경 변수 (.env 파일에만, 절대 코드에 직접 X)

- `DART_API_KEY` — https://opendart.fss.or.kr
- `ANTHROPIC_API_KEY` — https://console.anthropic.com

---

## 절대 규칙

- **Push 전 반드시 rebase pull:** `git pull --rebase origin main` 먼저, 그 다음 push
- **API 키 하드코딩 금지:** .env 파일에서만 불러오기
- **.env를 git에 커밋 금지**
- **모델 고정:** Anthropic API 호출 시 모델은 `claude-haiku-4-5` 사용 권장 (비용 절감)
- **UI 텍스트:** 전부 한국어

---

## 개발 순서 (추천)

| 단계 | 목표 |
|---|---|
| 1단계 | 환경 설정 (.env, requirements.txt) |
| 2단계 | data.py — DART API 연결 + SQLite 저장 |
| 3단계 | graph.py — LangGraph Supervisor 아키텍처 |
| 4단계 | report.py — RAG + fpdf2 PDF 생성 |
| 5단계 | app.py — Plotly 시각화 + LLM 연결 |
| 6단계 | Streamlit Cloud 배포 |

---

## 왜 DART API를 코드 스크립트로 짜는가

각 단계의 정확도가 90%라면 → 5단계 후 전체 정확도는 59%로 떨어집니다.

- **DART API 호출, SQLite 저장** → `data.py` 스크립트 (결정론적, 항상 같은 결과)
- **분석, 판단, 자연어 생성** → Claude API (claude-haiku-4-5)
