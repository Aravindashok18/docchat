import pytest


@pytest.mark.parametrize(
    "question, source, page",
    [
        ("How much water can the tank hold?", "aurora-x200-manual.pdf", 1),
        ("How often does the machine need descaling?", "aurora-x200-manual.pdf", 4),
        ("What does error E2 mean?", "aurora-x200-manual.pdf", 5),
        ("What is the fee for an international wire transfer?", "harborline-savings-terms.pdf", 3),
        ("When does an account become dormant?", "harborline-savings-terms.pdf", 4),
    ],
)
def test_best_hit_is_on_the_right_page(retriever, question, source, page):
    best = retriever.search(question)[0]
    assert (best.source, best.page) == (source, page)
    assert retriever.is_answerable([best])


@pytest.mark.parametrize("question", ["What is the capital of France?", "What is the weather forecast for tomorrow?"])
def test_off_topic_questions_are_not_answerable(retriever, question):
    assert not retriever.is_answerable(retriever.search(question))


def test_hits_are_sorted_closest_first(retriever):
    distances = [h.distance for h in retriever.search("how do I descale")]
    assert distances == sorted(distances)


def test_empty_result_is_not_answerable(retriever):
    assert not retriever.is_answerable([])
