"""Thin CDP observer wrapper for a Patchright/Playwright page."""
import asyncio

from .network_capture import NetworkRecorder


class CdpObserver:
    def __init__(self, page, source_id, capture_bodies=False):
        self.page = page
        self.recorder = NetworkRecorder(source_id, capture_bodies=capture_bodies)
        self.session = None

    async def start(self):
        self.session = await self.page.context.new_cdp_session(self.page)
        await self.session.send("Network.enable")
        self._requests = {}

        def on_request(event):
            self._requests[event.get("requestId")] = event.get("request", {})

        async def on_response(event):
            response = event.get("response", {})
            body = b""
            if self.recorder.capture_bodies:
                try:
                    payload = await self.session.send("Network.getResponseBody", {"requestId": event.get("requestId")})
                    body = payload.get("body", "").encode("utf-8")
                except Exception:
                    body = b""
            request = self._requests.get(event.get("requestId"), {})
            self.recorder.record_response(event.get("requestId", ""), response.get("url", ""), request.get("method", "GET"), response.get("status", 0), request.get("headers", {}), response.get("headers", {}), body, getattr(self.page, "url", ""))

        self.session.on("Network.requestWillBeSent", on_request)
        self.session.on("Network.responseReceived", lambda event: asyncio.create_task(on_response(event)))
        return self.session

    async def record_known_response(self, request_id, url, method, status, request_headers=None, response_headers=None, body=None):
        return self.recorder.record_response(request_id, url, method, status, request_headers, response_headers, body, getattr(self.page, "url", ""))

    async def stop(self):
        if self.session:
            await self.session.send("Network.disable")
