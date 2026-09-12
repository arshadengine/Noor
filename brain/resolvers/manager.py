"""
brain/resolvers/manager.py
─────────────────────────────────────────────────────
ResourceResolverManager.
Orchestrates multi-stage classification, confidence scoring, structured JSON diagnostics,
confidence gap disambiguation, and OS Knowledge Graph edge recording.
"""

import time
import json
from typing import Dict, Any, List
from brain.resolvers.base import BaseResourceResolver, ResourceType
from brain.resolvers.url import URLResolver
from brain.resolvers.application import ApplicationResolver
from brain.resolvers.folder import FolderResolver
from brain.resolvers.file import FileResolver
from brain.resolvers.settings import SettingsResolver
from brain.knowledge import add_knowledge_edge


class ResourceResolverManager:
    """Manager class that evaluates confidence scores across registered resolvers."""

    def __init__(self):
        self.resolvers: List[BaseResourceResolver] = [
            URLResolver(),
            SettingsResolver(),
            ApplicationResolver(),
            FolderResolver(),
            FileResolver(),
        ]

    def classify_and_resolve(self, target: str) -> Dict[str, Any]:
        """
        Classify and resolve target string into a typed resource payload with confidence score,
        structured JSON diagnostics, and gap disambiguation.
        """
        start_time = time.perf_counter()
        target_clean = target.strip()

        if not target_clean:
            return {
                "resource_type": ResourceType.UNKNOWN,
                "confidence": 0.0,
                "confidence_tier": "LOW",
                "resolved_target": "",
                "action": "none",
                "metadata": {},
                "diagnostics": {}
            }

        # 1. Evaluate confidence scores across all registered candidate resolvers
        candidates_log = []
        best_resolver = None
        best_score = 0.0
        second_best_score = 0.0

        for resolver in self.resolvers:
            r_name = resolver.__class__.__name__
            try:
                score = resolver.match(target_clean)
            except Exception:
                score = 0.0

            candidates_log.append({
                "resolver": r_name,
                "confidence": round(score, 2)
            })

            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_resolver = resolver
            elif score > second_best_score:
                second_best_score = score

        candidates_log.sort(key=lambda x: x["confidence"], reverse=True)
        exec_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # 2. Check Disambiguation Gap (if top 2 candidates are very close and confidence < 0.85)
        score_gap = round(best_score - second_best_score, 2)
        if best_score > 0.0 and score_gap <= 0.15 and best_score < 0.85:
            diag = {
                "input": target_clean,
                "winner": "Ambigous",
                "confidence": round(best_score, 2),
                "candidates": candidates_log,
                "execution_time_ms": exec_time_ms
            }
            print(f"[Resolver Debug Log]\n{json.dumps(diag, indent=2)}")

            return {
                "resource_type": ResourceType.UNKNOWN,
                "confidence": round(best_score, 2),
                "confidence_tier": "MEDIUM",
                "resolved_target": target_clean,
                "action": "clarify",
                "metadata": {
                    "candidates": candidates_log[:2],
                    "score_gap": score_gap
                },
                "diagnostics": diag
            }

        if best_resolver and best_score >= 0.50:
            payload = best_resolver.resolve(target_clean)
            confidence = payload.get("confidence", best_score)

            if confidence >= 0.85:
                tier = "HIGH"
            elif confidence >= 0.50:
                tier = "MEDIUM"
            else:
                tier = "LOW"

            payload["confidence_tier"] = tier

            diag = {
                "input": target_clean,
                "winner": best_resolver.__class__.__name__,
                "confidence": round(confidence, 2),
                "candidates": candidates_log,
                "execution_time_ms": exec_time_ms
            }
            payload["diagnostics"] = diag
            print(f"[Resolver Debug Log]\n{json.dumps(diag, indent=2)}")

            # Record edge into OS Knowledge Graph for context learning
            try:
                add_knowledge_edge(
                    source_name="User",
                    source_type="User",
                    relation="OPENED_RESOURCE",
                    target_name=payload["resolved_target"],
                    target_type=payload["resource_type"].value
                )
            except Exception:
                pass

            return payload

        # Fallback payload
        diag = {
            "input": target_clean,
            "winner": "None",
            "confidence": 0.0,
            "candidates": candidates_log,
            "execution_time_ms": exec_time_ms
        }
        return {
            "resource_type": ResourceType.UNKNOWN,
            "confidence": 0.0,
            "confidence_tier": "LOW",
            "resolved_target": target_clean,
            "action": "none",
            "metadata": {},
            "diagnostics": diag
        }
