from __future__ import annotations

from pathlib import Path
import json
import datetime as dt
from typing import Any, Dict, List


class MemoryStore:
    def __init__(self, namespace: str, base_path: Path | None = None):
        self.namespace = namespace
        self.base_path = base_path or Path(__file__).resolve().parent
        self.file = self.base_path / "memory_store.jsonl"
        self.file.touch(exist_ok=True)

    def add(self, entry: Dict[str, Any]) -> None:
        payload = {
            "ts": dt.datetime.utcnow().isoformat() + "Z",
            "ns": self.namespace,
            **entry,
        }
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 5) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            with self.file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        except FileNotFoundError:
            return []
        # filtrar por namespace y retornar últimos
        rows = [r for r in rows if r.get("ns") == self.namespace]
        return rows[-limit:]
