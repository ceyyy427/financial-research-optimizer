"""Unified Patchright/CDP navigation boundary for public source adapters.

This module owns browser lifecycle, navigation retries, selector waits, raw
response capture, screenshots, and failure snapshots.  It deliberately does
not parse or normalize financial data.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .patchright_runtime import PatchrightRuntime


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class NavigationResult:
    text: str
    url: str
    status: int | None
    content_type: str
    retrieved_at: str
    raw_file: str
    screenshot_file: str | None = None
    failure_snapshot: str | None = None


class NavigationError(RuntimeError):
    """Raised after navigation retries are exhausted."""

    def __init__(self, message: str, failure_snapshot: str | None = None):
        super().__init__(message)
        self.failure_snapshot = failure_snapshot


class BrowserNavigation:
    """Safe, retrying browser navigation for public or authorized pages."""

    def __init__(
        self,
        root: str | os.PathLike[str] = "artifacts/browser",
        source_id: str = "browser",
        context_name: str = "research_context",
        authorized: bool = False,
        headless: bool = True,
        cdp_endpoint: str | None = None,
        timeout_ms: int = 30_000,
        retries: int = 2,
        backoff_seconds: float = 0.5,
        runtime: PatchrightRuntime | None = None,
    ):
        self.root = Path(root)
        self.source_id = source_id
        self.timeout_ms = int(timeout_ms)
        self.retries = max(0, int(retries))
        self.backoff_seconds = max(0.0, float(backoff_seconds))
        self.runtime = runtime or PatchrightRuntime(
            root=self.root,
            context_name=context_name,
            authorized=authorized,
            headless=headless,
            cdp_endpoint=cdp_endpoint,
        )

    async def start(self):
        if self.runtime.cdp_endpoint:
            return await self.runtime.connect_over_cdp()
        return await self.runtime.start()

    async def close(self):
        await self.runtime.stop()

    async def recover(self):
        return await self.runtime.recover()

    async def _failure_snapshot(self, page, error: Exception, attempt: int) -> str:
        failure_dir = self.root / "failures" / self.source_id
        failure_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        base = failure_dir / f"{stamp}-attempt-{attempt}"
        html_path = base.with_suffix(".html")
        metadata_path = base.with_suffix(".json")
        screenshot_path = base.with_suffix(".png")
        try:
            html_path.write_text(await page.content(), encoding="utf-8")
        except Exception:
            html_path.write_text("", encoding="utf-8")
        screenshot = None
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            screenshot = str(screenshot_path)
        except Exception:
            screenshot_path = None
        metadata_path.write_text(
            json.dumps(
                {
                    "source_id": self.source_id,
                    "url": getattr(page, "url", ""),
                    "retrieved_at": _now(),
                    "attempt": attempt,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "html_file": str(html_path),
                    "screenshot_file": screenshot,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return str(metadata_path)

    async def fetch_text(
        self,
        url: str,
        wait_selector: str | None = None,
        wait_until: str = "domcontentloaded",
        screenshot: bool = False,
    ) -> NavigationResult:
        """Navigate to a public endpoint and return the visible response body."""
        last_error: Exception | None = None
        page = None
        for attempt in range(1, self.retries + 2):
            try:
                if self.runtime.context is None:
                    await self.start()
                page = await self.runtime.new_page()
                response = await page.goto(url, wait_until=wait_until, timeout=self.timeout_ms)
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
                status = getattr(response, "status", None)
                if callable(status):
                    status = status()
                if status is not None and int(status) >= 400:
                    raise NavigationError(f"HTTP {status} for {url}")
                body = ""
                if response is not None and hasattr(response, "body"):
                    try:
                        response_body = await response.body()
                        body = response_body.decode("utf-8", errors="replace") if isinstance(response_body, bytes) else str(response_body)
                    except Exception:
                        body = ""
                if not body.strip():
                    body = await page.locator("body").inner_text()
                if not body.strip():
                    body = await page.content()
                retrieved_at = _now()
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                raw_dir = self.root / "responses" / self.source_id
                raw_dir.mkdir(parents=True, exist_ok=True)
                raw_path = raw_dir / f"{digest}.raw"
                if not raw_path.exists():
                    raw_path.write_text(body, encoding="utf-8")
                screenshot_file = None
                if screenshot:
                    screenshot_path = raw_path.with_suffix(".png")
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    screenshot_file = str(screenshot_path)
                content_type = ""
                headers = getattr(response, "headers", {}) if response else {}
                if callable(headers):
                    headers = headers()
                if isinstance(headers, dict):
                    content_type = headers.get("content-type", "")
                return NavigationResult(body, getattr(page, "url", url), status, content_type, retrieved_at, str(raw_path), screenshot_file)
            except Exception as exc:  # browser providers must expose evidence on failure
                last_error = exc
                if page is not None:
                    snapshot = await self._failure_snapshot(page, exc, attempt)
                else:
                    snapshot = None
                if attempt > self.retries:
                    raise NavigationError(f"navigation failed after {attempt} attempts: {exc}", snapshot) from exc
                await asyncio.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
            finally:
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
                    page = None
        raise NavigationError(str(last_error or "navigation failed"))


def tls_policy_from_env() -> dict[str, Any]:
    """Return explicit TLS policy without silently weakening verification."""
    insecure = os.environ.get("FRO_TLS_INSECURE", "0").lower() in {"1", "true", "yes"}
    return {
        "verify": not insecure,
        "ca_file": os.environ.get("FRO_TLS_CA_FILE"),
        "insecure_requested": insecure,
        "warning": "TLS verification disabled by FRO_TLS_INSECURE" if insecure else None,
    }
