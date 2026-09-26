# Browser Adapter Contract

Browser access is a controlled fallback, not a replacement for official APIs. Patchright handles isolated contexts, navigation, authorized login checkpoints, filters, pagination, downloads, screenshots, and trace files. CDP observes Network/Page/Runtime/Target/Fetch/Tracing facts, including request URLs, response status, response hashes, and failures.

The required order is:

```text
official API → official download → authorized database → Patchright → CDP capture → DOM → OCR/vision
```

Browser adapters must save the raw download or captured response before parsing. They must preserve `source_id`, `access_method`, `request_url`, `response_status`, `content_type`, `retrieved_at`, `snapshot_hash`, `parser_version`, and authorization status. CAPTCHA, paywall, access-control, or login restrictions must cause `blocked` or `fallback`; they must not be bypassed.
