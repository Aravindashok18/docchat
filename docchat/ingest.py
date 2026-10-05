"""Ingestion: load -> clean -> chunk -> embed -> store in ChromaDB."""
import argparse
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from . import config
from .cleaning import clean_pages


@lru_cache(maxsize=2)
def get_embeddings(model_name: str = config.EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    # normalised vectors so that cosine distance = 1 - dot product
    return HuggingFaceEmbeddings(model_name=model_name, encode_kwargs={"normalize_embeddings": True})


def load_pages(path: Path) -> List[str]:
    """Raw text of each page; plain-text files count as a single page."""
    if path.suffix.lower() == ".pdf":
        return [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    return [path.read_text(encoding="utf-8")]


def load_clean_pages(docs_dir: Path) -> dict:
    """{filename: [cleaned text per page]} for every supported file in docs_dir."""
    files = sorted(p for p in Path(docs_dir).iterdir() if p.suffix.lower() in {".pdf", ".txt"})
    if not files:
        raise FileNotFoundError(f"no .pdf or .txt files in {docs_dir}")
    return {f.name: clean_pages(load_pages(f)) for f in files}


def split_documents(cleaned: dict, chunk_size: int, chunk_overlap: int) -> List[Document]:
    """Chunk page by page, so every chunk belongs to exactly one page."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for source, pages in cleaned.items():
        for page_number, text in enumerate(pages, start=1):
            for index, piece in enumerate(splitter.split_text(text)):
                chunks.append(
                    Document(
                        page_content=piece,
                        metadata={"source": source, "page": page_number, "chunk": index},
                    )
                )
    return chunks


def build_index(
    docs_dir: Path = config.DOCS_DIR,
    persist_dir: Path = config.CHROMA_DIR,
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: Optional[int] = None,
    embeddings=None,
) -> int:
    """Rebuild the vector store from scratch; returns the number of chunks stored."""
    if chunk_overlap is None:
        chunk_overlap = config.chunk_overlap(chunk_size)
    embeddings = embeddings or get_embeddings()
    chunks = split_documents(load_clean_pages(docs_dir), chunk_size, chunk_overlap)

    # Drop and recreate the collection rather than deleting the directory:
    # chromadb caches one client per path and breaks if the files vanish under it.
    def open_collection() -> Chroma:
        return Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
            collection_metadata={"hnsw:space": "cosine"},
        )

    open_collection().delete_collection()
    store = open_collection()
    ids = [f"{c.metadata['source']}:p{c.metadata['page']}:c{c.metadata['chunk']}" for c in chunks]
    store.add_documents(chunks, ids=ids)
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the DocChat vector index")
    parser.add_argument("--docs", type=Path, default=config.DOCS_DIR)
    parser.add_argument("--chunk-size", type=int, default=config.CHUNK_SIZE)
    args = parser.parse_args()
    count = build_index(docs_dir=args.docs, chunk_size=args.chunk_size)
    print(f"indexed {count} chunks from {args.docs} into {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
