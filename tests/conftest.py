import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docchat import config  # noqa: E402  (sets the telemetry env var before chromadb loads)
from docchat.generate import ExtractiveGenerator  # noqa: E402
from docchat.ingest import build_index, get_embeddings  # noqa: E402
from docchat.retrieval import Retriever, open_store  # noqa: E402
from docchat.service import ChatService  # noqa: E402


@pytest.fixture(scope="session")
def embeddings():
    return get_embeddings()


@pytest.fixture(scope="session")
def index_dir(tmp_path_factory, embeddings):
    path = tmp_path_factory.mktemp("chroma")
    build_index(docs_dir=config.DOCS_DIR, persist_dir=path, embeddings=embeddings)
    return path


@pytest.fixture(scope="session")
def retriever(index_dir, embeddings):
    return Retriever(open_store(embeddings, index_dir))


@pytest.fixture()
def service(retriever, embeddings):
    return ChatService(retriever, ExtractiveGenerator(embeddings, token_delay=0))
