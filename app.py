import json
import logging
import os

from flask import Flask, jsonify, send_from_directory
from flask_sock import Sock
from simple_websocket import ConnectionClosed

from docchat import config
from docchat.service import ChatService, get_service

log = logging.getLogger("docchat")
MAX_QUESTION_CHARS = 1000


def create_app(service: ChatService = None) -> Flask:
    """Build the Flask app. Tests pass a ready-made service; otherwise it is built on first use."""
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    sock = Sock(app)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/ingest")
    def ingest():
        """Re-read the docs folder and rebuild the index."""
        from docchat.ingest import build_index, get_embeddings
        from docchat.retrieval import Retriever, open_store

        embeddings = get_embeddings()
        count = build_index(embeddings=embeddings)
        # the rebuild replaces the collection, so point the live service at the new one
        svc = service or get_service()
        svc.retriever = Retriever(open_store(embeddings), config.TOP_K, config.MAX_DISTANCE)
        return jsonify(chunks=count)

    @sock.route("/ws")
    def chat(ws):
        while True:
            try:
                raw = ws.receive()
            except ConnectionClosed:
                return
            question = _parse_question(raw)
            if question is None:
                _send(ws, {"type": "error", "message": "Send JSON like {\"question\": \"...\"}."})
                continue
            try:
                for event in (service or get_service()).ask(question):
                    _send(ws, event)
            except ConnectionClosed:
                return
            except Exception:
                log.exception("failed to answer %r", question)
                _send(ws, {"type": "error", "message": "Something went wrong answering that."})

    return app


def _parse_question(raw):
    try:
        question = json.loads(raw)["question"]
    except (TypeError, ValueError, KeyError):
        return None
    if not isinstance(question, str) or not question.strip():
        return None
    return question.strip()[:MAX_QUESTION_CHARS]


def _send(ws, event: dict) -> None:
    ws.send(json.dumps(event))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 5000 is taken by AirPlay Receiver on recent macOS, so default to 5050
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", "5050")), threaded=True)
