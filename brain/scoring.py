"""
brain/scoring.py
─────────────────────────────────────────────────────
Multi-Factor Model Scoring & Ranking Engine for Noor.

Calculates weighted scores based on:
1. Capability Match (40%) + Dynamic Learning Adjustment
2. Provider Availability (20%)
3. Measured Latency Score (15%)
4. Historical Reliability Score (15%)
5. User Preference Score (10%)

Includes constraint filtering and close-score tie breaking (delta < 0.3).
"""

from __future__ import annotations
from typing import Any
from brain.registry import MODELS, TASK_CAPABILITY_MAP, check_constraints
from brain.health import health_monitor
from brain.telemetry import get_telemetry_stats

CAPABILITY_WEIGHT = 0.40
AVAILABILITY_WEIGHT = 0.20
LATENCY_WEIGHT = 0.15
RELIABILITY_WEIGHT = 0.15
PREFERENCE_WEIGHT = 0.10


def calculate_model_score(
    model_key: str,
    task_category: str,
    user_preference: str = "speed"
) -> float:
    """Calculate the composite score (0-10) for a given candidate model."""
    spec = MODELS[model_key]
    provider = spec["provider"]
    capabilities = spec.get("capabilities", {})

    # 1. Base Capability Rating for Task
    cap_key = TASK_CAPABILITY_MAP.get(task_category, "chat")
    base_cap = float(capabilities.get(cap_key, 7.0))

    # Learning Adjustment: Adjust capability slightly using telemetry success rate
    telemetry_stats = get_telemetry_stats()
    provider_stats = telemetry_stats.get(provider, {})
    success_rate = provider_stats.get("success_rate", 1.0)
    # If success rate > 95%, boost +0.4; if < 80%, penalty -0.8
    if success_rate >= 0.95:
        learning_adj = 0.4
    elif success_rate < 0.80:
        learning_adj = -0.8
    else:
        learning_adj = 0.0
    effective_capability = max(0.0, min(10.0, base_cap + learning_adj))

    # 2. Availability Score from Health Monitor
    availability_score = health_monitor.get_availability_score(provider)

    # 3. Latency Score from Health Monitor
    latency_score = health_monitor.get_latency_score(provider)

    # 4. Reliability Score from Health Monitor
    reliability_score = health_monitor.get_reliability_score(provider)

    # 5. User Preference Score
    if user_preference == "speed":
        preference_score = float(spec.get("speed_rating", 7))
    elif user_preference == "privacy":
        preference_score = 10.0 if spec.get("constraints", {}).get("offline") else 4.0
    elif user_preference == "coding":
        preference_score = float(capabilities.get("coding", 7))
    else:
        preference_score = 7.0

    total_score = (
        CAPABILITY_WEIGHT * effective_capability +
        AVAILABILITY_WEIGHT * availability_score +
        LATENCY_WEIGHT * latency_score +
        RELIABILITY_WEIGHT * reliability_score +
        PREFERENCE_WEIGHT * preference_score
    )

    return round(total_score, 2)


def rank_candidate_models(
    task_category: str,
    required_constraints: dict[str, Any] | None = None,
    user_preference: str = "speed"
) -> list[tuple[str, float]]:
    """
    Filter candidate models by constraints, compute scores, and rank them.
    Includes tie-breaker logic for close scores (delta < 0.3).
    """
    req_constraints = required_constraints or {}
    candidates: list[tuple[str, float]] = []

    for model_key in MODELS:
        valid, reason = check_constraints(model_key, req_constraints)
        if not valid:
            print(f"[Noor Scoring] Excluded model '{model_key}': {reason}")
            continue

        score = calculate_model_score(model_key, task_category, user_preference)
        candidates.append((model_key, score))

    # Sort descending by score
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Tie-Breaking (< 0.3 delta): If top 2 candidates are very close, favor the faster / higher speed rating
    if len(candidates) >= 2:
        top_key, top_score = candidates[0]
        sec_key, sec_score = candidates[1]

        if (top_score - sec_score) < 0.3:
            top_speed = MODELS[top_key].get("speed_rating", 5)
            sec_speed = MODELS[sec_key].get("speed_rating", 5)
            if sec_speed > top_speed:
                print(f"[Noor Scoring] Tie-break (<0.3 delta): Favoring faster model '{sec_key}' over '{top_key}'.")
                candidates[0], candidates[1] = candidates[1], candidates[0]

    return candidates
