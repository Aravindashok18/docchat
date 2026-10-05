from langchain_core.language_models.fake_chat_models import FakeListChatModel

from docchat.generate import ExtractiveGenerator, LLMGenerator, NOT_FOUND_TOKEN
from docchat.retrieval import Hit


def test_extractive_answer_contains_the_fact_and_cites_its_page(retriever, embeddings):
    question = "How much water can the tank hold?"
    hits = retriever.search(question)
    answer = ExtractiveGenerator(embeddings, token_delay=0).generate(question, hits)
    text = "".join(answer.tokens)
    assert "1.8 litres" in text
    assert [(h.source, h.page) for h in answer.cited] == [("aurora-x200-manual.pdf", 1)]


def test_extractive_streams_word_by_word(retriever, embeddings):
    question = "What temperature should I heat milk to?"
    answer = ExtractiveGenerator(embeddings, token_delay=0).generate(question, retriever.search(question))
    tokens = list(answer.tokens)
    assert len(tokens) > 5
    assert all(t.strip() and " " not in t.strip() for t in tokens)


def _hits():
    return [Hit("The tank holds 1.8 litres.", "manual.pdf", 1, 0.2), Hit("Descale monthly.", "manual.pdf", 4, 0.5)]


def test_llm_generator_streams_the_models_answer_and_cites_every_context_chunk():
    llm = FakeListChatModel(responses=["The tank holds 1.8 litres."])
    answer = LLMGenerator(llm).generate("How big is the tank?", _hits())
    tokens = list(answer.tokens)
    assert len(tokens) > 1  # streamed in pieces, not one blob
    assert "".join(tokens) == "The tank holds 1.8 litres."
    assert [h.page for h in answer.cited] == [1, 4]


def test_llm_not_found_sentinel_produces_no_tokens_even_when_streamed_per_character():
    llm = FakeListChatModel(responses=[NOT_FOUND_TOKEN])
    answer = LLMGenerator(llm).generate("Who is the CEO?", _hits())
    assert list(answer.tokens) == []


def test_llm_answer_shorter_than_the_sentinel_is_still_emitted():
    llm = FakeListChatModel(responses=["Yes."])
    assert "".join(LLMGenerator(llm).generate("Is it safe?", _hits()).tokens) == "Yes."


def test_llm_prompt_contains_context_with_page_labels():
    llm = FakeListChatModel(responses=["ok"])
    generator = LLMGenerator(llm)
    messages = generator.chain.first.invoke({"context": "[manual.pdf, page 1]\nx", "question": "q?"}).to_messages()
    assert "page 1" in messages[0].content and NOT_FOUND_TOKEN in messages[0].content
