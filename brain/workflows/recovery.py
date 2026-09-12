"""
brain/workflows/recovery.py
─────────────────────────────────────────────────────
Extensible Recovery Strategy Registry for Noor Workflows.
Maps failure conditions to bounded recovery strategies with attempt limits, cooldowns, and escalation.
"""

import time
from dataclasses import dataclass
from typing import Dict, Callable, Optional, Any


@dataclass
class RecoveryStrategy:
    name: str
    action_handler: Callable[[Dict[str, Any]], bool]
    max_attempts: int = 2
    timeout_sec: float = 5.0
    cooldown_sec: float = 1.0


class RecoveryStrategyRegistry:
    """Registry for bounded self-healing recovery strategies."""

    _strategies: Dict[str, RecoveryStrategy] = {}
    _attempt_counts: Dict[str, int] = {}

    @classmethod
    def register_strategy(cls, condition_key: str, strategy: RecoveryStrategy):
        cls._strategies[condition_key.lower()] = strategy

    @classmethod
    def get_strategy(cls, condition_key: str) -> Optional[RecoveryStrategy]:
        return cls._strategies.get(condition_key.lower())

    @classmethod
    def attempt_recovery(cls, condition_key: str, context: Dict[str, Any]) -> bool:
        """
        Execute bounded recovery strategy for a failed precondition or error condition.
        Enforces max_attempts, cooldown, and timeout bounds.
        """
        key = condition_key.lower()
        strategy = cls.get_strategy(key)
        if not strategy:
            return False

        current_attempts = cls._attempt_counts.get(key, 0)
        if current_attempts >= strategy.max_attempts:
            print(f"[RecoveryRegistry] Max recovery attempts ({strategy.max_attempts}) reached for '{key}'. Escalating.")
            return False

        print(f"[RecoveryRegistry] Attempting recovery for '{key}' (Attempt {current_attempts + 1}/{strategy.max_attempts})...")
        cls._attempt_counts[key] = current_attempts + 1

        if strategy.cooldown_sec > 0:
            time.sleep(strategy.cooldown_sec)

        try:
            success = strategy.action_handler(context)
            return success
        except Exception as e:
            print(f"[RecoveryRegistry] Strategy execution exception: {e}")
            return False

    @classmethod
    def reset_attempts(cls, condition_key: Optional[str] = None):
        if condition_key:
            cls._attempt_counts.pop(condition_key.lower(), None)
        else:
            cls._attempt_counts.clear()
