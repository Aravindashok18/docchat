"""The question -> events pipeline the WebSocket handler streams to the browser."""
import threading
from typing import Iterator, List

from . import config
from .generate import NOT_FOUND_MESSAGE, build_generator
from .ingest import build_index, get_embeddings
from .retrieval import Hit, Retriever, open_store, store_is_empty


def _sources(cited: List[Hit]) -> List[dict]:
    seen, out = set(), []
    for hit in cited:
        key = (hit.source, hit.page)
        if key not in seen:
            seen.add(key)
            out.append({"source": hit.source, "page": hit.page})
    return out


class ChatService:
    def __init__(self, retriever: Retriever, generator):
        self.retriever = retriever
        self.generator = generator

    def ask(self, question: str) -> Iterator[dict]:
        """Yield {"type": "token"|"not_found"|"done", ...} events for one question."""
        hits = self.retriever.search(question)
        if not self.retriever.is_answerable(hits):
            yield {"type": "not_found", "message": NOT_FOUND_MESSAGE}
            yield {"type": "done", "found": False, "sources": []}
            return

        answer = self.generator.generate(question, hits)
        first = next(answer.tokens, None)
        if first is None:  # the model decided the context had no answer
            yield {"type": "not_found", "message": NOT_FOUND_MESSAGE}
            yield {"type": "done", "found": False, "sources": []}
            return

        yield {"type": "token", "text": first}
        for token in answer.tokens:
            yield {"type": "token", "text": token}
        yield {"type": "done", "found": True, "sources": _sources(answer.cited)}


_lock = threading.Lock()
_service = None


def get_service() -> ChatService:
    """Build the default service once, indexing the docs folder on first run."""
    global _service
    with _lock:
        if _service is None:
            embeddings = get_embeddings()
            store = open_store(embeddings)
            if store_is_empty(store):
                build_index(embeddings=embeddings)
                store = open_store(embeddings)
            _service = ChatService(Retriever(store), build_generator(embeddings))
        return _service
