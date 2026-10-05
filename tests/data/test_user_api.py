import json

from finahinking.data.connection_settings import InMemoryDataCredentialStore
from finahinking.data.user_api import (
    DataConnectorError,
    JsonApiConnector,
    TransportResponse,
)
from finahinking.data.user_api_contracts import (
    DataConnectionConfig,
    DataRequest,
    DataSourceCredentialRef,
)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, url, *, headers, timeout, allow_redirects=False):
        self.calls.append((url, dict(headers), timeout, allow_redirects))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


PUBLIC_RESOLVER = lambda host, port=None: ("93.184.216.34",)


def config(auth_mode="no_auth", credential_ref=None):
    return DataConnectionConfig(
        "custom-feed", "Custom feed", "https://example.test/api", credential_ref, auth_mode,
        {"instrument": "ticker", "timestamp": "time", "close": "price"}, "data"
    )


def request():
    return DataRequest("prices", ("AAA",), "2026-01-01", "2026-01-03")


def response(payload, status=200, headers=None, url="https://example.test/api"):
    raw = json.dumps(payload).encode()
    return TransportResponse(status_code=status, headers=headers or {"content-type": "application/json"}, body=raw, url=url)


def test_json_api_normalizes_user_field_mapping():
    transport = FakeTransport([response({"data": [{"ticker": "AAA", "time": "2026-01-02", "price": "10"}]})])
    connector = JsonApiConnector(config(), InMemoryDataCredentialStore(), transport, resolver=PUBLIC_RESOLVER)
    batch = connector.fetch(request())
    assert batch.records[0]["instrument"] == "AAA"
    assert batch.records[0]["close"] == 10.0
    assert transport.calls[0][2] == 15.0
    assert transport.calls[0][3] is False


def test_bounded_transport_failures_are_secret_free():
    ref = DataSourceCredentialRef(env_var="FINAHINK_DATA_KEY")
    store = InMemoryDataCredentialStore({"FINAHINK_DATA_KEY": "super-secret"})
    cases = [
        response({"error": "no"}, status=401),
        response({"error": "rate"}, status=429),
        TimeoutError("super-secret"),
        response("not-json", headers={"content-type": "text/plain"}),
        response({"data": []}),
    ]
    for item in cases:
        transport = FakeTransport([item, item, item])
        try:
            JsonApiConnector(config("bearer", ref), store, transport, resolver=PUBLIC_RESOLVER).fetch(request())
        except DataConnectorError as exc:
            message = str(exc).lower()
            assert "super-secret" not in str(exc)
            assert "example.test" not in message


def test_connector_rejects_private_targets_and_cross_origin_redirects():
    for url in ("http://127.0.0.1/data", "http://169.254.169.254/latest", "ftp://example.test/data"):
        try:
            JsonApiConnector(DataConnectionConfig("x", "X", url, None, "no_auth", {}, None), InMemoryDataCredentialStore(), FakeTransport([]))
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe URL accepted")
    transport = FakeTransport([response({"data": []}, url="https://other.test/api")])
    try:
        JsonApiConnector(config(), InMemoryDataCredentialStore(), transport, resolver=PUBLIC_RESOLVER).fetch(request())
    except DataConnectorError as exc:
        assert "other.test" not in str(exc)


def test_resolved_private_addresses_are_rejected_deterministically():
    resolver = lambda host, port=None: ("127.0.0.1", "2001:db8::1")
    transport = FakeTransport([response({"data": []})])
    try:
        JsonApiConnector(config(), InMemoryDataCredentialStore(), transport, resolver=resolver).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "target"
        assert transport.calls == []
    else:
        raise AssertionError("resolved private target was accepted")


def test_pagination_cannot_change_origin_or_send_credentials_there():
    ref = DataSourceCredentialRef(env_var="FINAHINK_DATA_KEY")
    store = InMemoryDataCredentialStore({"FINAHINK_DATA_KEY": "super-secret"})
    transport = FakeTransport([response({"data": [], "next": "https://other.test/page"})])
    try:
        JsonApiConnector(config("bearer", ref), store, transport, resolver=PUBLIC_RESOLVER).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "redirect"
        assert "super-secret" not in repr(exc)
        assert len(transport.calls) == 1
    else:
        raise AssertionError("cross-origin pagination was accepted")


def test_transport_exception_cause_does_not_retain_secret():
    ref = DataSourceCredentialRef(env_var="FINAHINK_DATA_KEY")
    store = InMemoryDataCredentialStore({"FINAHINK_DATA_KEY": "super-secret"})
    transport = FakeTransport([RuntimeError("token=super-secret") for _ in range(3)])
    try:
        JsonApiConnector(config("bearer", ref), store, transport, resolver=PUBLIC_RESOLVER).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "transport"
        assert exc.__cause__ is None
        assert exc.__context__ is None
        assert "super-secret" not in repr(exc)
    else:
        raise AssertionError("transport failure unexpectedly succeeded")


def test_repeated_pagination_page_is_bounded():
    transport = FakeTransport([response({"data": [], "next": "/api"}), response({"data": [], "next": "/api"})])
    try:
        JsonApiConnector(config(), InMemoryDataCredentialStore(), transport, resolver=PUBLIC_RESOLVER).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "pagination"
        assert len(transport.calls) <= 2
    else:
        raise AssertionError("pagination loop was not rejected")


def test_authenticated_legacy_transport_is_rejected_before_secret_is_sent():
    class LegacyTransport:
        def __init__(self):
            self.calls = []

        def request(self, url, *, headers, timeout):
            self.calls.append((url, dict(headers)))
            return response({"data": []})

    ref = DataSourceCredentialRef(env_var="FINAHINK_DATA_KEY")
    transport = LegacyTransport()
    try:
        JsonApiConnector(config("bearer", ref), InMemoryDataCredentialStore({"FINAHINK_DATA_KEY": "super-secret"}), transport, resolver=PUBLIC_RESOLVER).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "transport_policy"
        assert transport.calls == []
        assert exc.__context__ is None
    else:
        raise AssertionError("legacy authenticated transport was accepted")


def test_dns_rebinding_is_checked_before_each_request():
    addresses = iter((("93.184.216.34",), ("127.0.0.1",)))

    def resolver(host, port=None):
        return next(addresses)

    transport = FakeTransport([response({"data": []})])
    try:
        JsonApiConnector(config(), InMemoryDataCredentialStore(), transport, resolver=resolver).fetch(request())
    except DataConnectorError as exc:
        assert exc.code == "target"
        assert transport.calls == []
    else:
        raise AssertionError("DNS rebinding was not rejected")
