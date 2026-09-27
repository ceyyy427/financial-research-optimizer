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
        self._reserved = {key: 0 for key in self._used}

    def reserve_estimate(self, network_requests=0, bytes_downloaded=0, artifacts=0, browser_contexts=0):
        """Atomically reserve a declared node estimate before work starts.

        The existing ``reserve`` method remains the compatibility path for
        measured consumption.  Adapters that know their upper bound can use
        this two-phase API and call ``commit_estimate`` or
        ``release_estimate`` when the node finishes.
        """
        requested = {
            "network_requests": int(network_requests or 0),
            "bytes_downloaded": int(bytes_downloaded or 0),
            "artifacts": int(artifacts or 0),
            "browser_contexts": int(browser_contexts or 0),
        }
        with self._lock:
            violations = []
            for key, amount in requested.items():
                if self._used[key] + self._reserved[key] + amount > int(self.limits[f"max_{key}"]):
                    violations.append(f"{key} would exceed {self.limits[f'max_{key}']}")
            if violations:
                return None, violations
            for key, amount in requested.items():
                self._reserved[key] += amount
            return requested, []

    def commit_estimate(self, reservation, actual=None):
        reservation = reservation or {}
        actual = actual or reservation
        with self._lock:
            for key, amount in reservation.items():
                self._reserved[key] = max(0, self._reserved[key] - int(amount or 0))
            for key, amount in actual.items():
                self._used[key] += int(amount or 0)

    def release_estimate(self, reservation):
        reservation = reservation or {}
        with self._lock:
            for key, amount in reservation.items():
                self._reserved[key] = max(0, self._reserved[key] - int(amount or 0))

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
                if self._used[key] + self._reserved[key] + amount > int(self.limits[f"max_{key}"]):
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
            return {**self._used, "reserved": dict(self._reserved), "wall_time_seconds": round(elapsed, 3), "limits": dict(self.limits)}
