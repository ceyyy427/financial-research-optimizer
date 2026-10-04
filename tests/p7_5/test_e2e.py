from __future__ import annotations

import json
import threading
from urllib.request import ProxyHandler, Request, build_opener

from finahinking.local_app import LocalAppConfig, LocalApplication, create_server


def _request(base: str, path: str, *, method: str = "GET", body: dict | None = None) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(base + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    # CI and developer shells may export an HTTP proxy.  A loopback smoke test
    # must never leave the machine or depend on proxy policy.
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=3) as response:
        raw = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
    return response.status, json.loads(raw) if "json" in content_type else raw


def test_http_smoke_covers_event_knowledge_quant_strategy_and_continuity(tmp_path) -> None:
    app = LocalApplication(LocalAppConfig(db_path=":memory:"))
    server = create_server(app, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, health = _request(base, "/api/health")
        assert status == 200 and health["status"] == "ok"
        status, events = _request(base, "/api/events")
        assert status == 200 and events["events"][0]["status"] == "CAPTURED"
        status, event_saved = _request(base, "/api/events/learn", method="POST", body={})
        assert status == 201 and event_saved["node_type"] == "event"
        status, knowledge = _request(base, "/api/knowledge?q=return")
        assert status == 200 and any(item["id"] == "return" for item in knowledge["concepts"])
        status, quant = _request(base, "/api/quant")
        assert status == 200 and quant["stage"] == "experiment"
        status, strategy = _request(base, "/api/strategy")
        assert status == 200 and strategy["real_money"] is False
        status, saved = _request(base, "/api/personal/save", method="POST", body={"title": "Saved journey", "payload": {"step": 1}})
        assert status == 201 and saved["saved"] is True
        status, personal = _request(base, "/api/personal")
        assert status == 200 and any(item["title"] == "Saved journey" for item in personal["nodes"])
        status, reopened = _request(base, "/api/reopen", method="POST", body={})
        assert status == 200 and reopened["reopened"] is True
        status, community = _request(base, "/api/community")
        assert status == 200 and community["leaderboards"] is False
        status, diagnostics = _request(base, "/api/diagnostics")
        assert status == 200 and diagnostics["offline"] is True
    finally:
        server.shutdown()
        server.server_close()
        app.close()
