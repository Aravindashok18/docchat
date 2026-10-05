import os
from pathlib import Path

from dotenv import load_dotenv

# chromadb phones home by default; keep the demo quiet and offline-friendly
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DOCS_DIR = Path(os.getenv("DOCS_DIR", ROOT / "data" / "docs"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / "chroma_store"))
COLLECTION_NAME = "docchat"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# CHUNK_SIZE / TOP_K / MAX_DISTANCE come from eval/run_eval.py (see README)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "150"))
CHUNK_OVERLAP_RATIO = 0.15
TOP_K = int(os.getenv("TOP_K", "2"))
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.58"))


def chunk_overlap(chunk_size: int = CHUNK_SIZE) -> int:
    return int(chunk_size * CHUNK_OVERLAP_RATIO)


# Optional: answer with an OpenAI chat model instead of extracting sentences.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Extractive mode has nothing to wait for, so tokens would arrive in one burst.
# A tiny pause per word lets the browser show them streaming in.
EXTRACTIVE_TOKEN_DELAY = float(os.getenv("EXTRACTIVE_TOKEN_DELAY", "0.02"))
