"""Thread-safe global resource budget for a research Plan DAG."""
from dataclasses import dataclass, field
from threading import Lock
import time


@dataclass
class BudgetManager:
    limits: dict = field(default_factory=dict)
    started_at: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        defaults = {
            "max_network_requests": 200,
            "max_bytes_downloaded": 500_000_000,
            "max_artifacts": 100,
            "max_wall_time_seconds": 1_800,
            "max_browser_contexts": 3,
        }
        self.limits = {**defaults, **(self.limits or {})}
        self._lock = Lock()
        self._used = {
            "network_requests": 0,
            "bytes_downloaded": 0,
            "artifacts": 0,
            "browser_contexts": 0,
        }

    def reserve(self, network_requests=0, bytes_downloaded=0, artifacts=0, browser_contexts=0):
        requested = {
            "network_requests": int(network_requests or 0),
            "bytes_downloaded": int(bytes_downloaded or 0),
            "artifacts": int(artifacts or 0),
            "browser_contexts": int(browser_contexts or 0),
        }
        with self._lock:
            elapsed = time.monotonic() - self.started_at
            violations = []
            for key, amount in requested.items():
                if self._used[key] + amount > int(self.limits[f"max_{key}"]):
                    violations.append(f"{key} would exceed {self.limits[f'max_{key}']}")
            if elapsed > float(self.limits["max_wall_time_seconds"]):
                violations.append(f"wall_time_seconds would exceed {self.limits['max_wall_time_seconds']}")
            if violations:
                return False, violations
            for key, amount in requested.items():
                self._used[key] += amount
            return True, []

    def snapshot(self):
        with self._lock:
            elapsed = time.monotonic() - self.started_at
            return {**self._used, "wall_time_seconds": round(elapsed, 3), "limits": dict(self.limits)}

