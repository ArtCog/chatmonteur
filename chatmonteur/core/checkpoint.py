"""Resumable checkpoints.

State for one project run lives in ``projects/<name>/.chatmonteur/checkpoint.json``.
Each completed step records its input hash + produced artifacts, so re-running a
pipeline skips work whose inputs haven't changed (saves time and paid API calls).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class Checkpoint:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, Any] = {"version": 1, "steps": {}}
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # Corrupt checkpoint: start clean rather than crash a long run.
                self._data = {"version": 1, "steps": {}}

    @classmethod
    def for_project(cls, project_root: Path) -> "Checkpoint":
        return cls(project_root / ".chatmonteur" / "checkpoint.json")

    def is_done(self, step_id: str, input_hash: str) -> bool:
        entry = self._data["steps"].get(step_id)
        return bool(entry) and entry.get("status") == "done" and entry.get("input_hash") == input_hash

    def artifacts(self, step_id: str) -> dict[str, str]:
        entry = self._data["steps"].get(step_id, {})
        return dict(entry.get("artifacts", {}))

    def record(self, step_id: str, input_hash: str, artifacts: dict[str, str], meta: dict | None = None) -> None:
        self._data["steps"][step_id] = {
            "status": "done",
            "input_hash": input_hash,
            "artifacts": artifacts,
            "meta": meta or {},
        }
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def hash_inputs(obj: Any) -> str:
        """Stable hash of a step's resolved params + upstream artifacts."""
        blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
