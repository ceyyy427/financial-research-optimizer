import threading
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from finahinking.data import connection_settings
from finahinking.data.connection_settings import (
    InMemoryDataCredentialStore,
    KeychainDataCredentialStore,
    KeychainError,
    MacOSKeychainBackend,
    new_local_credential_ref,
)
from finahinking.data.user_api_contracts import DataSourceCredentialRef
from finahinking.local_app import LocalAppConfig, LocalApplication, create_server


def make_app():
    return LocalApplication(LocalAppConfig(db_path=":memory:"), data_credential_store=InMemoryDataCredentialStore())


class FakeKeychain:
    def __init__(self):
        self.values = {}

    def get(self, label):
        return self.values.get(label)

    def put(self, label, value):
        self.values[label] = value


def test_keychain_store_uses_injected_backend_without_serializing_secret():
    backend = FakeKeychain()
    store = KeychainDataCredentialStore(backend)
    ref = DataSourceCredentialRef(keychain_label="finathink-data-test")
    store.put(ref, "super-secret")
    assert store.has(ref)
    assert store.resolve(ref) == "super-secret"
    assert "super-secret" not in repr(store)


def test_default_settings_store_uses_keychain_boundary():
    from finahinking.data.connection_settings import DataConnectionSettingsStore

    assert isinstance(DataConnectionSettingsStore().credentials, KeychainDataCredentialStore)


def test_macos_backend_does_not_leak_command_output_on_failure():
    backend = MacOSKeychainBackend(executable="/definitely/missing/security")
    try:
        backend.get("finathink-data-test")
    except KeychainError as exc:
        assert "missing" not in str(exc)
        assert "security" not in str(exc)
    else:
        raise AssertionError("missing keychain executable unexpectedly succeeded")


@pytest.mark.parametrize("connection_id", ["token-feed", "secret-data", "apikey", "credential-feed"])
def test_local_credential_ref_is_opaque_for_secret_like_connection_ids(connection_id):
    ref = new_local_credential_ref(connection_id)
    assert ref.keychain_label is not None
    assert ref.keychain_label.startswith("finathink-data-")
    assert connection_id not in ref.keychain_label


def test_macos_backend_does_not_place_secret_in_security_argv(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(connection_settings.subprocess, "run", fake_run)
    MacOSKeychainBackend(executable="security").put("finathink-data-label", "super-secret")
    argv, kwargs = calls[0]
    assert "super-secret" not in argv
    assert argv[-1] == "-w"
    assert kwargs["input"] == "super-secret"
    assert kwargs["shell"] is False


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
