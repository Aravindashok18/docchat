def _run(service, question):
    return list(service.ask(question))


def test_answerable_question_streams_tokens_then_done_with_sources(service):
    events = _run(service, "How often should I backflush the group head?")
    kinds = [e["type"] for e in events]
    assert kinds[-1] == "done" and set(kinds[:-1]) == {"token"}
    assert "once a week" in "".join(e["text"] for e in events if e["type"] == "token")
    done = events[-1]
    assert done["found"] is True
    assert done["sources"] == [{"source": "aurora-x200-manual.pdf", "page": 4}]


def test_off_topic_question_returns_not_found_and_no_sources(service):
    events = _run(service, "What is the capital of France?")
    assert [e["type"] for e in events] == ["not_found", "done"]
    assert events[-1] == {"type": "done", "found": False, "sources": []}
    assert "couldn't find" in events[0]["message"]
