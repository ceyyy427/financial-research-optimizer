"""Local route and UI-boundary tests for the P8.2 research workspace."""

from __future__ import annotations

import sqlite3

from finahinking.local_app import LocalApplication, create_server


def test_research_payload_is_server_normalized_and_provenance_bound() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    status, content_type, payload = app.route("GET", "/api/research/series")
    assert status == 200 and content_type == "application/json"
    assert payload["schema_version"] == 1
    assert payload["dataset"]["mode"] == "SAMPLE"
    assert payload["dataset"]["fingerprint"]
    assert payload["points"]
    assert all(point["provider"] == "finathink.fixture" for point in payload["points"])
    assert all("features" in point and "events" in point for point in payload["points"])
    assert payload["sweep"]["experiment_count"] == 6
    assert payload["sweep"]["multiple_testing"]["experiment_count"] == 6
    app.close()


def test_research_pages_and_local_asset_keep_external_execution_out() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    for path in ("/research", "/ml", "/parameter", "/settings/engines", "/settings/data-sources"):
        status, content_type, body = app.route("GET", path)
        assert status == 200 and content_type.startswith("text/html")
        assert "Finathink" in body
    research = app.route("GET", "/research")[2]
    assert 'data-finathink-research' in research
    assert '/api/research/series' in research
    assert '/assets/finathink-research.js' in research
    assert 'data-research-point-table' in research and '<tbody>' in research
    assert "script-src 'self'" in research
    assert "http://" not in research and "https://" not in research
    asset = app.route("GET", "/assets/finathink-research.js")
    assert asset[0] == 200 and asset[1].startswith("application/javascript")
    assert b"lightweight" in asset[2]
    app.close()


def test_research_api_is_read_only_and_qmt_status_is_explicit() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    status, _, capabilities = app.route("GET", "/api/research/capabilities")
    assert status == 200 and capabilities["qmt"]["status"] == "NOT CONNECTED"
    status, _, qmt = app.route("GET", "/api/research/qmt")
    assert status == 200 and qmt["read_only"] is True
    assert "order_stock" in qmt["denied"] and "cancel_order" in qmt["denied"]
    status, _, response = app.route("POST", "/api/research/series", body={})
    assert status == 404 and response["error"] == "route not found"
    app.close()


def test_http_research_response_sets_self_only_script_policy() -> None:
    import threading
    from urllib.request import ProxyHandler, Request, build_opener

    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    server = create_server(app, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        opener = build_opener(ProxyHandler({}))
        request = Request(f"http://127.0.0.1:{server.server_address[1]}/research")
        with opener.open(request, timeout=3) as response:
            body = response.read().decode("utf-8")
            csp = response.headers["Content-Security-Policy"]
        assert response.status == 200
        assert "script-src 'self'" in csp
        assert "finathink-research.js" in body
    finally:
        server.shutdown()
        server.server_close()
        app.close()
