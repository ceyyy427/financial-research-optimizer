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

    def request(self, url, *, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


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
    connector = JsonApiConnector(config(), InMemoryDataCredentialStore(), transport)
    batch = connector.fetch(request())
    assert batch.records[0]["instrument"] == "AAA"
    assert batch.records[0]["close"] == 10.0
    assert transport.calls[0][2] == 15.0


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
            JsonApiConnector(config("bearer", ref), store, transport).fetch(request())
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
        JsonApiConnector(config(), InMemoryDataCredentialStore(), transport).fetch(request())
    except DataConnectorError as exc:
        assert "other.test" not in str(exc)
