from dataclasses import dataclass
from pathlib import Path
from typing import List

from langchain_chroma import Chroma

from . import config


@dataclass(frozen=True)
class Hit:
    text: str
    source: str
    page: int
    distance: float  # cosine distance: 0 = identical direction, lower is closer


def open_store(embeddings, persist_dir: Path = config.CHROMA_DIR) -> Chroma:
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def store_is_empty(store: Chroma) -> bool:
    return not store.get(limit=1)["ids"]


class Retriever:
    def __init__(self, store: Chroma, k: int = config.TOP_K, max_distance: float = config.MAX_DISTANCE):
        self.store = store
        self.k = k
        self.max_distance = max_distance

    def search(self, question: str) -> List[Hit]:
        results = self.store.similarity_search_with_score(question, k=self.k)
        hits = [
            Hit(doc.page_content, doc.metadata["source"], doc.metadata["page"], float(score))
            for doc, score in results
        ]
        return sorted(hits, key=lambda h: h.distance)

    def is_answerable(self, hits: List[Hit]) -> bool:
        """False when nothing retrieved is close enough to the question to trust."""
        return bool(hits) and hits[0].distance <= self.max_distance
