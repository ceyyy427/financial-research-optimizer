from typing import ClassVar

import pytest

from finahinking.data.http_transport import BoundedHttpTransport, BoundedTransportError
from finahinking.data.user_api import TransportResponse


def test_transport_rejects_redirects_and_private_targets_by_default() -> None:
    transport = BoundedHttpTransport()
    with pytest.raises(BoundedTransportError, match="redirect"):
        transport.request("https://example.test/data", headers={}, allow_redirects=True)
    with pytest.raises(BoundedTransportError, match="target"):
        transport.request("http://127.0.0.1/data", headers={})


def test_transport_enforces_response_size_before_returning_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status = 200
        headers: ClassVar[dict[str, str]] = {"Content-Type": "application/json"}

        def __init__(self) -> None:
            self._read = False

        def geturl(self) -> str:
            return "https://example.test/data"

        def read(self, amount: int = -1) -> bytes:
            del amount
            return b"x" * 32

        def close(self) -> None:
            pass

    transport = BoundedHttpTransport(max_response_bytes=16)
    monkeypatch.setattr(transport, "_resolve", lambda host, port: ("93.184.216.34",))
    monkeypatch.setattr(transport, "_open", lambda *args, **kwargs: Response())
    with pytest.raises(BoundedTransportError, match="size"):
        transport.request("https://example.test/data", headers={})


def test_transport_returns_typed_response_and_never_follows_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status = 200
        headers: ClassVar[dict[str, str]] = {"Content-Type": "application/json"}

        def __init__(self) -> None:
            self._read = False

        def geturl(self) -> str:
            return "https://example.test/data"

        def read(self, amount: int = -1) -> bytes:
            del amount
            if self._read:
                return b""
            self._read = True
            return b'{"data": []}'

        def close(self) -> None:
            pass

    transport = BoundedHttpTransport()
    monkeypatch.setattr(transport, "_resolve", lambda host, port: ("93.184.216.34",))
    monkeypatch.setattr(transport, "_open", lambda *args, **kwargs: Response())
    response = transport.request("https://example.test/data", headers={})
    assert isinstance(response, TransportResponse)
    assert response.status_code == 200
    assert response.body == b'{"data": []}'


@pytest.mark.parametrize("query_key", ["api_key", "token", "password", "authorization", "X-Api-Key"])
def test_transport_rejects_sensitive_query_parameters(monkeypatch: pytest.MonkeyPatch, query_key: str) -> None:
    transport = BoundedHttpTransport()
    monkeypatch.setattr(transport, "_resolve", lambda host, port: ("93.184.216.34",))
    with pytest.raises(BoundedTransportError, match="query"):
        transport.request(f"https://example.test/data?{query_key}=value", headers={})
