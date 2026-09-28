import json
from pathlib import Path
from types import SimpleNamespace

from adapters.tonghuashun import TonghuashunAdapter
from execute_online_refresh import execute_data_refresh
from parsers import parse
from browser.navigation import BrowserNavigation, tls_policy_from_env


ROOT = Path(__file__).resolve().parents[1]


JSONP = 'quotebridge_v4_line_hs_000001_01_last({"name":"平安银行","data":"20260923,11,11.5,10.8,11.2,1000,12000;20260924,11.2,11.4,11.1,11.3,1200,13500"})'


def test_tonghuashun_jsonp_parser_emits_canonical_input_rows():
    rows = parse("tonghuashun_jsonp", JSONP, instrument_id="000001", source_url="https://d.10jqka.com.cn/")
    assert len(rows) == 2
    assert rows[0]["field"] == "close"
    assert rows[1]["value"] == 11.3
    assert rows[1]["point_in_time_status"] == "not_available"


def test_tonghuashun_adapter_snapshots_and_normalizes(tmp_path):
    raw_file = tmp_path / "response.raw"
    raw_file.write_text(JSONP, encoding="utf-8")

    class FakeNavigation:
        async def fetch_text(self, url, screenshot=False):
            return SimpleNamespace(
                text=JSONP,
                url=url,
                status=200,
                content_type="application/javascript",
                retrieved_at="2026-09-27T00:00:00Z",
                raw_file=str(raw_file),
            )

    profile = {
        "source_id": "10jqka",
        "name": "同花顺",
        "authority": "secondary_aggregator",
        "primary_method": "browser",
        "parser": "tonghuashun_jsonp",
        "base_urls": ["https://www.10jqka.com.cn/"],
    }
    adapter = TonghuashunAdapter(profile, snapshot_dir=tmp_path / "snapshots", navigation=FakeNavigation())
    result = adapter.fetch(instrument_id="000001")
    assert len(result["observations"]) == 2
    assert result["snapshot"]["source_id"] == "10jqka"
    assert Path(result["snapshot"]["raw_file"]).exists()


def test_execute_online_refresh_dispatches_tonghuashun(tmp_path):
    class FakeNavigation:
        async def fetch_text(self, url, screenshot=False):
            raw_file = tmp_path / "response.raw"
            raw_file.write_text(JSONP, encoding="utf-8")
            return SimpleNamespace(text=JSONP, url=url, status=200, content_type="application/javascript", retrieved_at="2026-09-27T00:00:00Z", raw_file=str(raw_file))

    result = execute_data_refresh(
        "10jqka",
        "https://d.10jqka.com.cn/v4/line/hs_000001/01/last.js",
        tmp_path / "run",
        params={"instrument_id": "000001"},
        registry_path=ROOT / "config/source_registry.yaml",
        navigation=FakeNavigation(),
    )
    assert result["status"] == "passed"
    assert result["normalized_rows"] == 2
    normalized = json.loads(Path(result["normalized_file"]).read_text(encoding="utf-8"))
    assert normalized[0]["source_id"] == "10jqka"


def test_tls_verification_is_on_by_default(monkeypatch):
    monkeypatch.delenv("FRO_TLS_INSECURE", raising=False)
    policy = tls_policy_from_env()
    assert policy["verify"] is True
    assert policy["insecure_requested"] is False


def test_browser_navigation_retries_and_writes_raw_response(tmp_path):
    class FakeResponse:
        status = 200
        headers = {"content-type": "application/javascript"}

        async def body(self):
            return JSONP.encode("utf-8")

    class FakePage:
        def __init__(self):
            self.url = "https://example.test/data"
            self.calls = 0

        async def goto(self, url, wait_until, timeout):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient browser failure")
            return FakeResponse()

        async def locator(self, selector):
            return self

        async def inner_text(self):
            return JSONP

        async def content(self):
            return "<html><body>failure</body></html>"

        async def screenshot(self, path, full_page=True):
            Path(path).write_bytes(b"png")

        async def close(self):
            return None

    class FakeRuntime:
        cdp_endpoint = None

        def __init__(self):
            self.context = None
            self.page = FakePage()

        async def start(self):
            self.context = object()

        async def new_page(self):
            return self.page

        async def stop(self):
            return None

    navigation = BrowserNavigation(root=tmp_path, source_id="test", retries=1, backoff_seconds=0, runtime=FakeRuntime())
    result = __import__("asyncio").run(navigation.fetch_text("https://example.test/data"))
    assert result.text.startswith("quotebridge_v4")
    assert Path(result.raw_file).read_text(encoding="utf-8") == JSONP
    assert list((tmp_path / "failures" / "test").glob("*.json"))
