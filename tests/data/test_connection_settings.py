import threading
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

from finahinking.local_app import LocalAppConfig, LocalApplication, create_server


def make_app():
    return LocalApplication(LocalAppConfig(db_path=":memory:"))


def test_connection_does_not_require_vendor_admission():
    app = make_app()
    try:
        status, _, payload = app.route("POST", "/api/data/connections", body={
            "_csrf": app.csrf_token,
            "connection_id": "private-feed",
            "display_name": "My private feed",
            "base_url": "https://example.test/api",
            "auth_mode": "no_auth",
            "field_mapping": {"instrument": "ticker", "timestamp": "time", "close": "price"},
            "records_path": "data",
        })
        assert status == 201
        assert payload["connection_id"] == "private-feed"
        assert payload["credential_configured"] is False
    finally:
        app.close()


def test_local_form_consumes_csrf_once_and_writes_connection():
    app = make_app()
    server = create_server(app, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        values = {
            "_csrf": app.csrf_token,
            "connection_id": "form-feed",
            "display_name": "Form feed",
            "base_url": "https://example.test/api",
            "auth_mode": "no_auth",
            "field_mapping": '{"instrument":"ticker","timestamp":"time","close":"price"}',
            "records_path": "data",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/data/connections",
            data=urlencode(values).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": f"http://127.0.0.1:{server.server_port}"},
            method="POST",
        )
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
            assert response.status == 201
        assert app.route("GET", "/api/data/connections")[2]["connections"][0]["connection_id"] == "form-feed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        app.close()


def test_connection_settings_hide_key_and_require_local_request():
    app = make_app()
    try:
        body = {
            "_csrf": app.csrf_token,
            "connection_id": "private-feed",
            "display_name": "My private feed",
            "base_url": "https://example.test/api",
            "auth_mode": "api_key_header",
            "auth_header": "X-API-Key",
            "api_key": "super-secret",
            "field_mapping": {"instrument": "ticker", "timestamp": "time", "close": "price"},
        }
        assert app.route("POST", "/api/data/connections", body=body)[0] == 201
        status, _, payload = app.route("GET", "/api/data/connections")
        assert status == 200
        assert "super-secret" not in str(payload)
        assert payload["connections"][0]["credential_configured"] is True
        assert app.route("POST", "/api/data/connections", body={**body, "_csrf": "wrong"})[0] == 403
        assert app.route("POST", "/api/data/connections/private-feed/test", body={"_csrf": "wrong"})[0] == 403
        status, _, page = app.route("GET", "/settings/data-connections")
        assert status == 200 and "super-secret" not in page
    finally:
        app.close()
