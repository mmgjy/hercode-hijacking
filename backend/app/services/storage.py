"""Snapshot storage.

Defaults to a local directory. If Supabase is configured, the service-role key
stays server-side only (never exposed to the frontend). For the hackathon scope
we keep local file storage; the function signature is stable so a Supabase
Storage backend can be dropped in.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.config import get_settings

_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe(name: str) -> str:
    return _SAFE.sub("_", name)[:80]


def save_snapshot(run_id: str, source_key: str, text: str, *, kind: str = "global") -> str:
    settings = get_settings()
    base = Path(settings.STORAGE_DIR) / kind / _safe(run_id)
    base.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]
    path = base / f"{_safe(source_key)}-{digest}.html"
    path.write_text(text, encoding="utf-8")
    return str(path)
