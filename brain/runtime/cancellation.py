"""
brain/runtime/cancellation.py
─────────────────────────────────────────────────────
Cooperative Cancellation Token for Noor Runtime.
Checked by execution loops during step transitions to halt safely without abrupt thread termination.
"""

from typing import Optional


class CancellationToken:
    """Cooperative cancellation token."""

    def __init__(self, reason: str = ""):
        self._is_cancelled = False
        self._reason = reason

    def cancel(self, reason: str = "User requested cancellation"):
        self._is_cancelled = True
        self._reason = reason

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def reason(self) -> str:
        return self._reason
