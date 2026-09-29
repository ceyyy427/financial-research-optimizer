"""Stable public error types for clients of the research runtime."""


class ResearchRuntimeError(RuntimeError):
    """Base error raised at the public API boundary."""


class ResearchBlockedError(ResearchRuntimeError):
    """The declared contract cannot be executed safely."""


class ArtifactNotFoundError(ResearchRuntimeError):
    """The requested registered artifact is not available."""
