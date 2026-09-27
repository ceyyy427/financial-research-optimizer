"""Optional Patchright runtime with explicit CDP and auth lifecycles."""
import os
from pathlib import Path
from .session_manager import context_path, validate_context_request


class PatchrightUnavailable(RuntimeError):
    pass


class PatchrightRuntime:
    def __init__(self, root="artifacts/browser", context_name="research_context", authorized=False, headless=True, storage_state_path=None, cdp_endpoint=None):
        self.root = root
        self.context_name = context_name
        self.authorized = authorized
        self.headless = headless
        self.storage_state_path = storage_state_path
        self.cdp_endpoint = cdp_endpoint
        self.connection_mode = "launch"
        self.browser_version = None
        self.contexts = []
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self):
        validate_context_request(self.context_name, self.authorized)
        try:
            from patchright.async_api import async_playwright
        except ImportError as exc:
            raise PatchrightUnavailable("Patchright is optional; install the browser extra before using browser access") from exc
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.connection_mode = "launch"
        return await self._new_context()

    async def connect_over_cdp(self, endpoint=None):
        """Attach to an existing browser; never launches a second browser."""
        validate_context_request(self.context_name, self.authorized)
        try:
            from patchright.async_api import async_playwright
        except ImportError as exc:
            raise PatchrightUnavailable("Patchright is optional; install the browser extra before using browser access") from exc
        endpoint = endpoint or self.cdp_endpoint
        if not endpoint:
            raise ValueError("cdp endpoint is required for connect_over_cdp")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(endpoint)
        self.connection_mode = "cdp"
        return await self._new_context(attach_existing=True)

    async def _new_context(self, attach_existing=False):
        if self.browser:
            try:
                self.browser_version = self.browser.version
            except Exception:
                self.browser_version = None
        insecure_tls = os.environ.get("FRO_TLS_INSECURE", "0").lower() in {"1", "true", "yes"}
        options = {"accept_downloads": True, "ignore_https_errors": insecure_tls}
        if self.context_name == "authorized_context" and self.authorized:
            state_path = context_path(self.root, self.context_name) / "storage_state.json"
            if self.storage_state_path:
                state_path = Path(self.storage_state_path)
                if not state_path.is_absolute():
                    state_path = context_path(self.root, self.context_name) / state_path
            if state_path.exists():
                options["storage_state"] = str(state_path)
        existing = list(getattr(self.browser, "contexts", []) or [])
        self.context = existing[0] if attach_existing and existing else await self.browser.new_context(**options)
        self.contexts = list(getattr(self.browser, "contexts", []) or [self.context])
        return self.context

    async def recover(self):
        """Reattach after a browser crash/closed transport."""
        await self.stop()
        if self.cdp_endpoint:
            return await self.connect_over_cdp(self.cdp_endpoint)
        return await self.start()

    def status(self):
        pages = list(getattr(self.context, "pages", []) or []) if self.context else []
        return {
            "connection_mode": self.connection_mode,
            "browser_version": self.browser_version,
            "context_name": self.context_name,
            "authorized": self.authorized,
            "context_count": len(self.contexts),
            "page_count": len(pages),
            "pages": [
                {
                    "url": getattr(page, "url", ""),
                    "frame_count": len(list(getattr(page, "frames", []) or [])),
                    "popup_capable": True,
                }
                for page in pages
            ],
        }

    def target_inventory(self):
        """Return a safe tab/frame inventory without reading page content."""
        return self.status().get("pages", [])

    async def new_page(self):
        if not self.context:
            raise RuntimeError("Patchright runtime is not started")
        return await self.context.new_page()

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            if self.connection_mode == "launch":
                await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.context = None
        self.contexts = []
        self.browser = None
        self.playwright = None
