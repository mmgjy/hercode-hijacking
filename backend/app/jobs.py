"""Replaceable background-job interface.

The default runner uses FastAPI BackgroundTasks (fine for a hackathon
deployment). The ``JobRunner`` protocol keeps the interface swappable for a real
queue (RQ, Celery, Arq) without touching the API layer. Tests can run jobs
synchronously via ``run_now``.
"""
from __future__ import annotations

from typing import Protocol

from fastapi import BackgroundTasks

from app.services.discovery_service import run_discovery


class JobRunner(Protocol):
    def enqueue_discovery(self, run_id: str) -> None: ...


class BackgroundTaskRunner:
    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._bg = background_tasks

    def enqueue_discovery(self, run_id: str) -> None:
        self._bg.add_task(run_discovery, run_id)


def run_now(run_id: str) -> None:
    """Synchronous execution helper for tests / CLI."""
    run_discovery(run_id)
