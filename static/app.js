(() => {
  const log = document.getElementById("log");
  const form = document.getElementById("form");
  const input = document.getElementById("question");
  const send = document.getElementById("send");
  const status = document.getElementById("status");

  let socket = null;
  let current = null; // the assistant bubble currently being streamed into

  function setStatus(state, label) {
    status.dataset.state = state;
    status.textContent = label;
  }

  function bubble(kind, text) {
    const el = document.createElement("div");
    el.className = "msg " + kind;
    const body = document.createElement("span");
    body.className = "text";
    body.textContent = text || "";
    el.appendChild(body);
    log.appendChild(el);
    el.scrollIntoView({ block: "end" });
    return el;
  }

  function addSources(el, sources) {
    if (!sources || !sources.length) return;
    const wrap = document.createElement("div");
    wrap.className = "sources";
    for (const s of sources) {
      const tag = document.createElement("span");
      tag.className = "source";
      tag.textContent = `${s.source} · p.${s.page}`;
      wrap.appendChild(tag);
    }
    el.appendChild(wrap);
  }

  function finish() {
    if (current) current.classList.remove("streaming");
    current = null;
    send.disabled = false;
    input.focus();
  }

  function handle(event) {
    if (event.type === "token") {
      if (!current) {
        current = bubble("bot streaming", "");
      }
      current.querySelector(".text").textContent += event.text;
      current.scrollIntoView({ block: "end" });
    } else if (event.type === "not_found") {
      bubble("bot not-found", event.message);
    } else if (event.type === "error") {
      bubble("bot error", event.message);
      finish();
    } else if (event.type === "done") {
      if (current) addSources(current, event.sources);
      finish();
    }
  }

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}/ws`);
    socket.onopen = () => setStatus("open", "connected");
    socket.onmessage = (msg) => handle(JSON.parse(msg.data));
    socket.onclose = () => {
      setStatus("closed", "disconnected, retrying…");
      finish();
      setTimeout(connect, 1500);
    };
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question || !socket || socket.readyState !== WebSocket.OPEN) return;
    bubble("user", question);
    socket.send(JSON.stringify({ question }));
    input.value = "";
    send.disabled = true;
  });

  connect();
})();
