"""Optional Patchright runtime; it never decides data validity or research scope."""
from .session_manager import context_path, validate_context_request


class PatchrightUnavailable(RuntimeError):
    pass


class PatchrightRuntime:
    def __init__(self, root="artifacts/browser", context_name="research_context", authorized=False, headless=True, storage_state_path=None):
        self.root = root
        self.context_name = context_name
        self.authorized = authorized
        self.headless = headless
        self.storage_state_path = storage_state_path
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
        options = {"accept_downloads": True}
        if self.context_name == "authorized_context" and self.authorized:
            state_path = context_path(self.root, self.context_name) / "storage_state.json"
            if self.storage_state_path:
                state_path = context_path(self.root, self.context_name) / self.storage_state_path
            if state_path.exists():
                options["storage_state"] = str(state_path)
        self.context = await self.browser.new_context(**options)
        return self.context

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
