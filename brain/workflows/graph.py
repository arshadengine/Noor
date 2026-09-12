"""
brain/workflows/graph.py
─────────────────────────────────────────────────────
Workflow Graph Engine for Noor Workflow Orchestration.
Performs DAG validation, cycle detection, topological sorting, ready-node discovery, and parallel task grouping.
"""

from collections import deque
from typing import Dict, List, Set, Tuple
from brain.workflows.schemas import WorkflowPlan, WorkflowTask


class WorkflowGraphEngine:
    """DAG Graph Engine for Workflow Dependency Graphs."""

    @staticmethod
    def validate_dag(plan: WorkflowPlan) -> Tuple[bool, str]:
        """
        Validate DAG structure: check for missing dependency links and cycle detection.
        Returns (is_valid, error_message).
        """
        task_ids = {t.task_id for t in plan.tasks}
        in_degree: Dict[str, int] = {t.task_id: 0 for t in plan.tasks}
        adj_list: Dict[str, List[str]] = {t.task_id: [] for t in plan.tasks}

        # Build adjacency list & verify dependency existence
        for task in plan.tasks:
            for dep_id in task.depends_on:
                if dep_id not in task_ids:
                    return False, f"Task '{task.task_id}' depends on non-existent task '{dep_id}'."
                adj_list[dep_id].append(task.task_id)
                in_degree[task.task_id] += 1

        # Kahn's algorithm for cycle detection
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(plan.tasks):
            return False, "Circular dependency cycle detected in workflow DAG graph."

        return True, "OK"

    @staticmethod
    def get_ready_tasks(plan: WorkflowPlan, completed_ids: Set[str], failed_ids: Set[str]) -> List[WorkflowTask]:
        """
        Find all tasks whose dependencies are fully satisfied and ready for execution.
        """
        ready = []
        for task in plan.tasks:
            if task.task_id in completed_ids or task.task_id in failed_ids or task.status == "RUNNING":
                continue

            # Check if all dependencies are in completed_ids
            deps_met = all(dep in completed_ids for dep in task.depends_on)
            if deps_met:
                ready.append(task)
        return ready

    @staticmethod
    def get_topological_sort(plan: WorkflowPlan) -> List[WorkflowTask]:
        """Return tasks in topologically sorted execution order."""
        task_map = {t.task_id: t for t in plan.tasks}
        in_degree: Dict[str, int] = {t.task_id: len(t.depends_on) for t in plan.tasks}
        adj_list: Dict[str, List[str]] = {t.task_id: [] for t in plan.tasks}

        for task in plan.tasks:
            for dep_id in task.depends_on:
                adj_list[dep_id].append(task.task_id)

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        sorted_tasks = []

        while queue:
            node = queue.popleft()
            if node in task_map:
                sorted_tasks.append(task_map[node])
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_tasks
