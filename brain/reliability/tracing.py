"""
brain/reliability/tracing.py
─────────────────────────────────────────────────────
Task Tracing & Observability Context for Noor (Phase 2.5).
Propagates a single immutable trace_id across Planner -> Executor -> Verifier -> Workflow -> History -> Telemetry.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class TraceSpan:
    span_id: str = field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    name: str = ""
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: Optional[float] = None
    status: str = "RUNNING"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "OK"):
        self.end_time = datetime.now().timestamp()
        self.status = status

    def duration_ms(self) -> float:
        end = self.end_time or datetime.now().timestamp()
        return round((end - self.start_time) * 1000.0, 2)


@dataclass
class TaskTraceContext:
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    workflow_id: Optional[str] = None
    spans: List[TraceSpan] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def start_span(self, span_name: str, metadata: Optional[Dict[str, Any]] = None) -> TraceSpan:
        span = TraceSpan(name=span_name, metadata=metadata or {})
        self.spans.append(span)
        return span

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "spans": [
                {
                    "span_id": s.span_id,
                    "name": s.name,
                    "duration_ms": s.duration_ms(),
                    "status": s.status,
                    "metadata": s.metadata,
                }
                for s in self.spans
            ],
            "created_at": self.created_at,
        }
