import os
import numpy as np
import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def _build_docs(result_df: pd.DataFrame) -> list[str]:
    docs = []
    for _, row in result_df.iterrows():
        text = (
            f"{row['회사명']}은 {row['섹터']} 섹터의 {row['투자단계']} 단계 투자사다. "
            f"투자금액은 {int(row['투자금액_백만원']):,}백만원이며 "
            f"MOIC {row['MOIC']}x, IRR {row['IRR(%)']}%, "
            f"DPI {row['DPI']}x, RVPI {row['RVPI']}x, TVPI {row['TVPI']}x이다."
        )
        docs.append(text)
    return docs


def answer_question(result_df: pd.DataFrame, question: str) -> str:
    docs = _build_docs(result_df)

    doc_embeddings = _model.encode(docs)
    q_embedding = _model.encode([question])[0]

    scores = np.dot(doc_embeddings, q_embedding) / (
        np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(q_embedding) + 1e-9
    )
    top_idx = np.argsort(scores)[::-1][:3]
    context = "\n".join(docs[i] for i in top_idx)

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"아래 포트폴리오 데이터를 참고하여 질문에 한국어로 간결하게 답하세요.\n\n"
                f"[포트폴리오 데이터]\n{context}\n\n"
                f"[질문]\n{question}"
            ),
        }],
    )
    return response.content[0].text
