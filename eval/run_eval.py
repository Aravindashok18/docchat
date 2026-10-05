"""Tune chunk size and top-k against a question set with known answers.

For every (chunk size, k) pair the script indexes the sample documents, retrieves
the top-k chunks for each question, and scores the retrieval + "not found" gate
end to end:

  * answerable question   -> correct if the known answer text is in the top-k
                             chunks AND the best chunk is close enough not to be refused
  * unanswerable question -> correct if the best chunk is too far away, so it is refused

The "not found" distance threshold is tuned separately for each (chunk size, k).

    python -m eval.run_eval
"""
import argparse
import csv
import json
import tempfile
from pathlib import Path
from statistics import mean, median

from docchat import config
from docchat.ingest import build_index, get_embeddings, load_clean_pages
from docchat.retrieval import Retriever, open_store

HERE = Path(__file__).resolve().parent


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def load_questions(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(questions: dict, cleaned: dict) -> None:
    """Every known answer must really be on its labelled page, or the eval is meaningless."""
    for q in questions["answerable"]:
        page_text = normalise(cleaned[q["source"]][q["page"] - 1])
        if normalise(q["answer"]) not in page_text:
            raise ValueError(f"{q['id']}: answer {q['answer']!r} not found on {q['source']} p.{q['page']}")
    corpus = normalise(" ".join(p for pages in cleaned.values() for p in pages))
    for q in questions["unanswerable"]:
        if q.get("must_be_absent") and normalise(q["must_be_absent"]) in corpus:
            raise ValueError(f"{q['id']}: marked unanswerable but corpus mentions it")


THRESHOLDS = [round(0.30 + 0.01 * i, 2) for i in range(71)]  # 0.30 .. 1.00


def collect(chunk_size, ks, questions, docs_dir, embeddings):
    """Retrieve for every question once; per-k answer checks are slices of the same top-k_max list."""
    with tempfile.TemporaryDirectory() as tmp:
        n_chunks = build_index(docs_dir=docs_dir, persist_dir=Path(tmp), chunk_size=chunk_size, embeddings=embeddings)
        retriever = Retriever(open_store(embeddings, Path(tmp)), k=max(ks))
        answerable = []
        for q in questions["answerable"]:
            hits = retriever.search(q["question"])
            answerable.append(
                {
                    "distance": hits[0].distance,
                    "top1_page_ok": (hits[0].source, hits[0].page) == (q["source"], q["page"]),
                    "found_at": {k: any(normalise(q["answer"]) in normalise(h.text) for h in hits[:k]) for k in ks},
                    "context_chars": {k: sum(len(h.text) for h in hits[:k]) for k in ks},
                }
            )
        unanswerable = [retriever.search(q["question"])[0].distance for q in questions["unanswerable"]]
    return n_chunks, answerable, unanswerable


def score(answerable, unanswerable, k, threshold):
    """(answered correctly, refused correctly) as rates, for one k and one threshold."""
    answered = mean(1.0 if a["found_at"][k] and a["distance"] <= threshold else 0.0 for a in answerable)
    refused = mean(1.0 if d > threshold else 0.0 for d in unanswerable)
    return answered, refused


def overall(answerable, unanswerable, k, threshold):
    answered, refused = score(answerable, unanswerable, k, threshold)
    n_a, n_u = len(answerable), len(unanswerable)
    return (answered * n_a + refused * n_u) / (n_a + n_u)


def best_threshold(answerable, unanswerable, k):
    """Threshold with the best overall accuracy; ties resolve to the middle of the tied range."""
    scored = [(overall(answerable, unanswerable, k, t), t) for t in THRESHOLDS]
    top = max(s for s, _ in scored)
    return round(median(t for s, t in scored if s >= top - 1e-9), 2)


def evaluate_chunk_size(chunk_size, ks, questions, docs_dir, embeddings):
    n_chunks, answerable, unanswerable = collect(chunk_size, ks, questions, docs_dir, embeddings)
    rows = []
    for k in ks:
        t = best_threshold(answerable, unanswerable, k)
        answered, refused = score(answerable, unanswerable, k, t)
        rows.append(
            {
                "chunk_size": chunk_size,
                "chunk_overlap": config.chunk_overlap(chunk_size),
                "k": k,
                "n_chunks": n_chunks,
                "answer_in_context": round(mean(1.0 if a["found_at"][k] else 0.0 for a in answerable), 4),
                "top1_page_correct": round(mean(1.0 if a["top1_page_ok"] else 0.0 for a in answerable), 4),
                "avg_context_chars": round(mean(a["context_chars"][k] for a in answerable), 1),
                "threshold": t,
                "answered_correctly": round(answered, 4),
                "refused_correctly": round(refused, 4),
                "overall_accuracy": round(overall(answerable, unanswerable, k, t), 4),
            }
        )
    return rows, answerable, unanswerable


def pick_best(rows):
    """Best end-to-end accuracy; among ties the smallest prompt (fewest context chars)."""
    top = max(r["overall_accuracy"] for r in rows)
    tied = [r for r in rows if r["overall_accuracy"] >= top - 1e-9]
    return min(tied, key=lambda r: (r["avg_context_chars"], r["k"]))


def threshold_table(answerable, unanswerable, k):
    """Gate behaviour across thresholds for one (chunk size, k)."""
    table = []
    for t in THRESHOLDS:
        answered, refused = score(answerable, unanswerable, k, t)
        table.append(
            {
                "threshold": t,
                "answered_correctly": round(answered, 4),
                "refused_correctly": round(refused, 4),
                "overall_accuracy": round(overall(answerable, unanswerable, k, t), 4),
            }
        )
    return table


def leave_one_out(answerable, unanswerable, k):
    """Overall accuracy when each question is scored with a threshold tuned on all the others.

    The headline numbers pick the threshold on the same questions they report, which is
    optimistic; this is the honest estimate for unseen questions.
    """
    items = [("a", i) for i in range(len(answerable))] + [("u", i) for i in range(len(unanswerable))]
    correct = 0
    for kind, i in items:
        rest_a = [a for j, a in enumerate(answerable) if not (kind == "a" and j == i)]
        rest_u = [d for j, d in enumerate(unanswerable) if not (kind == "u" and j == i)]
        t = best_threshold(rest_a, rest_u, k)
        if kind == "a":
            held = answerable[i]
            correct += 1 if held["found_at"][k] and held["distance"] <= t else 0
        else:
            correct += 1 if unanswerable[i] > t else 0
    return correct / len(items)


def write_csv(path: Path, rows) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, default=HERE / "questions.json")
    parser.add_argument("--docs", type=Path, default=config.DOCS_DIR)
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=[150, 250, 400, 600, 800, 1200])
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--out-dir", type=Path, default=HERE)
    args = parser.parse_args()

    questions = load_questions(args.questions)
    validate(questions, load_clean_pages(args.docs))
    embeddings = get_embeddings()

    all_rows, data = [], {}
    for size in args.chunk_sizes:
        rows, answerable, unanswerable = evaluate_chunk_size(size, args.ks, questions, args.docs, embeddings)
        all_rows.extend(rows)
        data[size] = (answerable, unanswerable)
        print(f"chunk_size={size:5d}: " + "  ".join(f"k={r['k']}:{r['overall_accuracy']:.2f}" for r in rows))

    best = pick_best(all_rows)
    answerable, unanswerable = data[best["chunk_size"]]
    loo = leave_one_out(answerable, unanswerable, best["k"])

    write_csv(args.out_dir / "results.csv", all_rows)
    write_csv(args.out_dir / "threshold.csv", threshold_table(answerable, unanswerable, best["k"]))

    print(f"\n{len(questions['answerable'])} answerable + {len(questions['unanswerable'])} unanswerable questions")
    print(f"best: chunk_size={best['chunk_size']} k={best['k']} threshold={best['threshold']}")
    print(f"  answer in retrieved context (no gate): {best['answer_in_context']:.3f}")
    print(f"  top-1 chunk is the labelled page:      {best['top1_page_correct']:.3f}")
    print(f"  answerable, answered correctly:        {best['answered_correctly']:.3f}")
    print(f"  unanswerable, correctly refused:       {best['refused_correctly']:.3f}")
    print(f"  overall (tuned on these questions):    {best['overall_accuracy']:.3f}")
    print(f"  overall (leave-one-out threshold):     {loo:.3f}")
    print(f"\nset CHUNK_SIZE={best['chunk_size']} TOP_K={best['k']} MAX_DISTANCE={best['threshold']}")


if __name__ == "__main__":
    main()
