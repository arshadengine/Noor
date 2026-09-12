"""
brain/workflows/background.py
─────────────────────────────────────────────────────
Managed Worker Pool for Noor Background Workflows.
Executes non-blocking long-running workflows asynchronously in managed worker threads.
"""

import threading
import queue
from typing import Callable, Any, Optional


class WorkerPool:
    """Managed background worker thread pool for Noor workflows."""

    _instance = None
    _task_queue: queue.Queue = queue.Queue()
    _threads: list[threading.Thread] = []
    _is_running = False

    def __new__(cls, num_workers: int = 3):
        if cls._instance is None:
            cls._instance = super(WorkerPool, cls).__new__(cls)
            cls._task_queue = queue.Queue()
            cls._threads = []
            cls._is_running = False
            cls.start_pool(num_workers)
        return cls._instance

    @classmethod
    def start_pool(cls, num_workers: int = 3):
        if cls._is_running:
            return
        cls._is_running = True
        cls._threads = []

        for i in range(num_workers):
            t = threading.Thread(target=cls._worker_loop, daemon=True, name=f"NoorWorkflowWorker-{i+1}")
            t.start()
            cls._threads.append(t)

    @classmethod
    def _worker_loop(cls):
        while cls._is_running:
            try:
                func, args, kwargs = cls._task_queue.get(timeout=1.0)
                try:
                    func(*args, **kwargs)
                except Exception as ex:
                    print(f"[WorkerPool Note] Task exception in worker: {ex}")
                finally:
                    cls._task_queue.task_done()
            except queue.Empty:
                continue

    @classmethod
    def submit(cls, func: Callable, *args, **kwargs):
        """Submit a workflow function to run asynchronously in background pool."""
        cls.start_pool()
        cls._task_queue.put((func, args, kwargs))

    @classmethod
    def shutdown(cls):
        cls._is_running = False
