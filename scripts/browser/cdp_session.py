"""CDP observer for Patchright/Playwright pages.

Response bodies are requested only after ``Network.loadingFinished``.  The
event log stores hashes and file paths; body bytes are never embedded in the
network manifest.
"""
import asyncio
from pathlib import Path

from .network_capture import NetworkRecorder


class CdpObserver:
    def __init__(self, page, source_id, capture_bodies=False, raw_body_dir="artifacts/browser/raw_bodies", required_domains=None):
        self.page = page
        self.recorder = NetworkRecorder(source_id, capture_bodies=capture_bodies, raw_body_dir=raw_body_dir)
        self.session = None
        self.required_domains = tuple(required_domains or ("Network", "Page"))
        self.domain_status = {}
        self._requests = {}
        self._responses = {}
        self._finished = set()
        self._body_tasks = set()

    async def start(self):
        self.session = await self.page.context.new_cdp_session(self.page)
        for domain in self.required_domains:
            try:
                await self.session.send(f"{domain}.enable")
                self.domain_status[domain] = "enabled"
            except Exception as exc:
                self.domain_status[domain] = f"unavailable: {exc}"

        def on_request(event):
            self._requests[event.get("requestId")] = event.get("request", {})

        async def capture_finished(request_id):
            event = self._responses.get(request_id)
            if not event:
                return
            response = event.get("response", {})
            body = b""
            if self.recorder.capture_bodies:
                try:
                    payload = await self.session.send("Network.getResponseBody", {"requestId": request_id})
                    body_text = payload.get("body", "")
                    body = body_text.encode("utf-8")
                except Exception:
                    body = b""
            request = self._requests.get(request_id, {})
            self.recorder.record_response(request_id, response.get("url", ""), request.get("method", "GET"), response.get("status", 0), request.get("headers", {}), response.get("headers", {}), body, getattr(self.page, "url", ""))

        def schedule_body(event):
            request_id = event.get("requestId")
            self._finished.add(request_id)
            task = asyncio.create_task(capture_finished(request_id))
            self._body_tasks.add(task)
            task.add_done_callback(self._body_tasks.discard)

        def on_response(event):
            request_id = event.get("requestId")
            self._responses[request_id] = event
            # Some CDP fakes and implementations do not emit loadingFinished;
            # the response is still retained, but getResponseBody is never
            # called before the finished event.

        def on_failed(event):
            request_id = event.get("requestId")
            self._responses.pop(request_id, None)

        self.session.on("Network.requestWillBeSent", on_request)
        self.session.on("Network.responseReceived", on_response)
        self.session.on("Network.loadingFinished", schedule_body)
        self.session.on("Network.loadingFailed", on_failed)
        return self.session

    async def record_known_response(self, request_id, url, method, status, request_headers=None, response_headers=None, body=None):
        return self.recorder.record_response(request_id, url, method, status, request_headers, response_headers, body, getattr(self.page, "url", ""))

    async def stop(self):
        if self.session:
            if self._body_tasks:
                await asyncio.gather(*tuple(self._body_tasks), return_exceptions=True)
            for domain in self.required_domains:
                try:
                    await self.session.send(f"{domain}.disable")
                except Exception:
                    pass
            self.session = None

    def manifest(self):
        return {"domain_status": self.domain_status, "records": self.recorder.records, "capture_bodies": self.recorder.capture_bodies}
