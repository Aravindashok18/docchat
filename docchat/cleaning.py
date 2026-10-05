"""Turn raw per-page PDF text into clean prose before chunking."""
import re
import unicodedata
from collections import Counter
from typing import List

_PAGE_NUMBER = re.compile(r"^(page\s*)?\d+(\s*(of|/)\s*\d+)?$", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-z])")
# header/footer candidates are looked for in the first and last few lines
_EDGE_LINES = 3
# a line is boilerplate if it shows up (digits aside) on at least this share of pages
_REPEAT_SHARE = 0.6
_MIN_PAGES_FOR_BOILERPLATE = 3
# running headers/footers are short; this keeps templated body lines ("Step 1: ...") safe
_MAX_BOILERPLATE_CHARS = 60


def _signature(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def find_boilerplate(pages: List[str]) -> set:
    """Signatures of header/footer lines that repeat across pages."""
    if len(pages) < _MIN_PAGES_FOR_BOILERPLATE:
        return set()
    seen = Counter()
    for page in pages:
        lines = [ln for ln in page.splitlines() if ln.strip()]
        edges = lines[:_EDGE_LINES] + lines[-_EDGE_LINES:]
        seen.update({_signature(ln) for ln in edges if len(ln.strip()) <= _MAX_BOILERPLATE_CHARS})
    cutoff = _REPEAT_SHARE * len(pages)
    return {sig for sig, count in seen.items() if count >= cutoff}


def clean_page(text: str, boilerplate: set) -> str:
    text = unicodedata.normalize("NFKC", text)  # also folds ligatures like "ﬁ" -> "fi"
    text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")

    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and (_PAGE_NUMBER.match(stripped) or (len(stripped) <= _MAX_BOILERPLATE_CHARS and _signature(stripped) in boilerplate)):
            continue
        kept.append(stripped)
    text = "\n".join(kept)

    text = _HYPHEN_BREAK.sub(r"\1", text)  # "restric-\ntions" -> "restrictions"
    # blank lines separate paragraphs; single newlines are just line wrapping
    paragraphs = [re.sub(r"\s*\n\s*", " ", p) for p in re.split(r"\n{2,}", text)]
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in paragraphs]
    return "\n\n".join(p for p in paragraphs if p)


def clean_pages(pages: List[str]) -> List[str]:
    """Clean every page of one document; the output list keeps page alignment."""
    boilerplate = find_boilerplate(pages)
    return [clean_page(p, boilerplate) for p in pages]
