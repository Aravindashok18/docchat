import json
from pathlib import Path

from docchat import config
from docchat.ingest import load_clean_pages, split_documents

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "eval" / "questions.json").read_text())


def test_every_chunk_belongs_to_exactly_one_page_with_metadata():
    cleaned = load_clean_pages(config.DOCS_DIR)
    chunks = split_documents(cleaned, chunk_size=300, chunk_overlap=45)
    assert chunks
    for chunk in chunks:
        assert set(chunk.metadata) == {"source", "page", "chunk"}
        page_text = cleaned[chunk.metadata["source"]][chunk.metadata["page"] - 1]
        assert chunk.page_content in page_text
        assert len(chunk.page_content) <= 300


def test_headers_and_page_numbers_do_not_leak_into_chunks():
    chunks = split_documents(load_clean_pages(config.DOCS_DIR), chunk_size=400, chunk_overlap=60)
    text = " ".join(c.page_content for c in chunks)
    assert "User Manual" not in text.replace("Aurora X200 Espresso Machine - User Manual", "")
    assert "Page 3" not in text


def test_labelled_answers_really_are_on_their_labelled_pages():
    cleaned = load_clean_pages(config.DOCS_DIR)
    for q in QUESTIONS["answerable"]:
        page = " ".join(cleaned[q["source"]][q["page"] - 1].lower().split())
        assert " ".join(q["answer"].lower().split()) in page, q["id"]
