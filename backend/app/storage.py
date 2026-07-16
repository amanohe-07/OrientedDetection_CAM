from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock
from typing import Any


class JsonStore:
    _replace_attempts = 6

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(self, relative_path: str | Path, data: Any) -> Path:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        with self._lock:
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
            for attempt in range(self._replace_attempts):
                try:
                    temporary.replace(destination)
                    break
                except PermissionError:
                    if attempt == self._replace_attempts - 1:
                        raise
                    # Windows may briefly lock a JSON file while another service scans it.
                    time.sleep(0.05 * (attempt + 1))
        return destination

    def read(self, relative_path: str | Path, default: Any = None) -> Any:
        source = self.root / relative_path
        if not source.exists():
            return default
        with self._lock:
            return json.loads(source.read_text(encoding="utf-8"))

    def list_json(self, relative_directory: str | Path) -> list[dict]:
        directory = self.root / relative_directory
        if not directory.exists():
            return []
        items = []
        for path in sorted(directory.glob("*.json"), reverse=True):
            try:
                with self._lock:
                    items.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return items
