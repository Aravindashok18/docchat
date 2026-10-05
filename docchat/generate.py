"""Answer generation: stream tokens for a question given the retrieved chunks."""
import re
import time
from dataclasses import dataclass
from typing import Iterator, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from . import config
from .retrieval import Hit

NOT_FOUND_MESSAGE = "I couldn't find that in the documents."
NOT_FOUND_TOKEN = "NOT_FOUND"

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
# an extra sentence is only added if it is nearly as relevant as the best one;
# otherwise the answer gets padded and cites pages that did not really answer
_RELATIVE_SCORE_FLOOR = 0.85
_MIN_WORDS = 3  # drops fragments such as a lone "." left over from chunking


@dataclass
class GeneratedAnswer:
    tokens: Iterator[str]
    cited: List[Hit]  # chunks whose pages should be cited next to the answer


# ---------------------------------------------------------------- extractive

class ExtractiveGenerator:
    """No LLM: return the retrieved sentences that best match the question.

    Runs anywhere with no API key. Sentences are scored against the question
    with the same embedding model used for retrieval.
    """

    def __init__(self, embeddings, max_sentences: int = 2, token_delay: float = config.EXTRACTIVE_TOKEN_DELAY):
        self.embeddings = embeddings
        self.max_sentences = max_sentences
        self.token_delay = token_delay

    def generate(self, question: str, hits: List[Hit]) -> GeneratedAnswer:
        candidates = []  # (hit rank, position in chunk, sentence, hit)
        for rank, hit in enumerate(hits):
            for position, sentence in enumerate(_SENTENCE_END.split(hit.text)):
                if len(sentence.split()) >= _MIN_WORDS:
                    candidates.append((rank, position, sentence.strip(), hit))
        if not candidates:
            return GeneratedAnswer(iter(()), [])

        question_vec = self.embeddings.embed_query(question)
        sentence_vecs = self.embeddings.embed_documents([c[2] for c in candidates])
        scores = [sum(q * s for q, s in zip(question_vec, vec)) for vec in sentence_vecs]

        ranked = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
        best = [i for i in ranked[: self.max_sentences] if scores[i] >= _RELATIVE_SCORE_FLOOR * scores[ranked[0]]]
        chosen = [candidates[i] for i in sorted(best, key=lambda i: candidates[i][:2])]

        cited, seen = [], set()
        for _, _, _, hit in chosen:
            if (hit.source, hit.page) not in seen:
                seen.add((hit.source, hit.page))
                cited.append(hit)
        # the splitter drops the ". " it splits on, so restore a closing period
        text = " ".join(c[2] if c[2][-1] in ".!?" else c[2] + "." for c in chosen)
        return GeneratedAnswer(self._stream_words(text), cited)

    def _stream_words(self, text: str) -> Iterator[str]:
        words = text.split()
        for i, word in enumerate(words):
            if self.token_delay:
                time.sleep(self.token_delay)
            yield word if i == len(words) - 1 else word + " "


# ----------------------------------------------------------------------- LLM

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You answer questions using only the context below. Be concise. "
            f"If the context does not contain the answer, reply with exactly {NOT_FOUND_TOKEN} "
            "and nothing else. Do not use outside knowledge.\n\nContext:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


class LLMGenerator:
    """Stream an answer from a LangChain chat model grounded in the retrieved chunks."""

    def __init__(self, llm):
        self.chain = _PROMPT | llm | StrOutputParser()

    def generate(self, question: str, hits: List[Hit]) -> GeneratedAnswer:
        context = "\n\n".join(f"[{h.source}, page {h.page}]\n{h.text}" for h in hits)
        stream = self.chain.stream({"context": context, "question": question})
        return GeneratedAnswer(self._guard(stream), hits)

    @staticmethod
    def _guard(stream: Iterator[str]) -> Iterator[str]:
        """Hold back the first few characters: if the model says NOT_FOUND, emit nothing.

        Tokens can be a single character, so buffer until there is enough text
        to tell the sentinel apart from a real answer.
        """
        buffer = ""
        decided = False
        for token in stream:
            if decided:
                yield token
                continue
            buffer += token
            if len(buffer) >= len(NOT_FOUND_TOKEN):
                decided = True
                if buffer.strip().upper().startswith(NOT_FOUND_TOKEN):
                    return
                yield buffer
        if not decided and buffer and not buffer.strip().upper().startswith(NOT_FOUND_TOKEN):
            yield buffer


def build_generator(embeddings):
    """LLM-backed generator when OPENAI_API_KEY is set, extractive otherwise."""
    if config.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("OPENAI_API_KEY is set but langchain-openai is missing: "
                               "pip install -r requirements-llm.txt") from exc
        return LLMGenerator(ChatOpenAI(model=config.LLM_MODEL, temperature=0, streaming=True))
    return ExtractiveGenerator(embeddings)
