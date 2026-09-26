"""Small deterministic retry policy for provider requests."""
from dataclasses import dataclass
import time


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.25
    max_backoff_seconds: float = 4.0
    retry_statuses: tuple = (408, 425, 429, 500, 502, 503, 504)

    def run(self, operation):
        last_error = None
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                result = operation()
                status = getattr(result, "status", None)
                if status in self.retry_statuses and attempt < self.max_attempts:
                    time.sleep(min(self.max_backoff_seconds, self.backoff_seconds * (2 ** (attempt - 1))))
                    continue
                return result
            except Exception as exc:  # provider adapters convert final failures to ProviderError
                last_error = exc
                if attempt >= self.max_attempts:
                    raise
                time.sleep(min(self.max_backoff_seconds, self.backoff_seconds * (2 ** (attempt - 1))))
        if last_error:
            raise last_error
        raise RuntimeError("retry policy completed without a result")
