import json
import threading

import pytest
from simple_websocket import Client
from werkzeug.serving import make_server

from app import create_app


@pytest.fixture()
def server_url(service):
    server = make_server("127.0.0.1", 0, create_app(service), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"ws://127.0.0.1:{server.server_port}/ws", f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


def _ask(ws_url, payload):
    client = Client.connect(ws_url)
    try:
        client.send(payload if isinstance(payload, str) else json.dumps(payload))
        events = []
        while True:
            event = json.loads(client.receive(timeout=20))
            events.append(event)
            if event["type"] in {"done", "error"}:
                return events
    finally:
        client.close()


def test_answer_arrives_as_separate_token_messages_followed_by_the_cited_page(server_url):
    ws_url, _ = server_url
    events = _ask(ws_url, {"question": "How often does the machine need descaling?"})
    tokens = [e for e in events if e["type"] == "token"]
    assert len(tokens) > 3
    assert "every 3 months" in "".join(t["text"] for t in tokens)
    assert events[-1]["sources"] == [{"source": "aurora-x200-manual.pdf", "page": 4}]


def test_unanswerable_question_gets_not_found_over_the_socket(server_url):
    ws_url, _ = server_url
    events = _ask(ws_url, {"question": "What is the weather forecast for tomorrow?"})
    assert [e["type"] for e in events] == ["not_found", "done"]


def test_invalid_payload_returns_an_error_and_keeps_the_connection_usable(server_url):
    ws_url, _ = server_url
    client = Client.connect(ws_url)
    try:
        client.send("not json")
        assert json.loads(client.receive(timeout=10))["type"] == "error"
        client.send(json.dumps({"question": "What does error E2 mean?"}))
        last = None
        while last is None or last["type"] != "done":
            last = json.loads(client.receive(timeout=20))
        assert last["found"] is True
    finally:
        client.close()


def test_index_page_and_health_endpoint(server_url):
    import urllib.request

    _, base = server_url
    with urllib.request.urlopen(base + "/health") as r:
        assert json.load(r) == {"status": "ok"}
    with urllib.request.urlopen(base + "/") as r:
        assert b"DocChat" in r.read()
