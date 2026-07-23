"""
memory.py — 이게 이 프로젝트의 "RAG" 파트.

각 NPC는 자기만의 MemoryStream을 갖고, 매 턴마다 지금 상황과 관련된 기억을
검색(retrieve)해서 LLM 프롬프트에 주입한다. 벡터DB 대신 TF-IDF + 코사인
유사도를 쓰는 이유는: 별도 임베딩 API 키/과금이 필요 없고, 메모리 수십~수백 개
규모에서는 속도도 충분하기 때문. 시간이 남으면 voyage/openai 임베딩으로
교체해도 구조는 그대로 유지된다 (retrieve() 내부만 바꾸면 됨).

점수식(recency + importance + relevance)은 스탠퍼드 Generative Agents
논문(Park et al., 2023, "스몰빌")의 기억 검색 아이디어를 단순화해서 따온 것.
"""

import math
import time
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class MemoryItem:
    content: str
    timestamp: float
    importance: float  # 1~10
    kind: str = "observation"  # observation | dialogue | reflection


IMPORTANT_KEYWORDS = ["싸움", "고백", "사고", "방문객", "정전", "이별", "축하", "위기"]


def rate_importance(text: str) -> float:
    """규칙 기반 중요도 채점. 시간 여유가 있으면 LLM 호출로 바꿔 더 정교하게 만들 수 있음."""
    return 8.0 if any(k in text for k in IMPORTANT_KEYWORDS) else 3.0


class MemoryStream:
    def __init__(self):
        self.memories: list[MemoryItem] = []

    def add(self, content: str, importance: float | None = None, kind: str = "observation"):
        if importance is None:
            importance = rate_importance(content)
        self.memories.append(
            MemoryItem(content=content, timestamp=time.time(), importance=importance, kind=kind)
        )

    def retrieve(self, query: str, k: int = 5) -> list[MemoryItem]:
        """recency(최근성) + importance(중요도) + relevance(관련성) 가중합으로 상위 k개 반환."""
        if not self.memories:
            return []
        if len(self.memories) <= k:
            return sorted(self.memories, key=lambda m: -m.timestamp)

        texts = [m.content for m in self.memories] + [query]
        vectorizer = TfidfVectorizer().fit(texts)
        vecs = vectorizer.transform(texts)
        sims = cosine_similarity(vecs[-1], vecs[:-1])[0]

        now = time.time()
        scored = []
        for i, m in enumerate(self.memories):
            recency = math.exp(-(now - m.timestamp) / 600)  # 10분 반감기 (틱 간격에 맞춰 조정 가능)
            score = 0.5 * sims[i] + 0.3 * (m.importance / 10) + 0.2 * recency
            scored.append((score, m))
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:k]]

    def recent(self, n: int = 3) -> list[MemoryItem]:
        return sorted(self.memories, key=lambda m: -m.timestamp)[:n]
