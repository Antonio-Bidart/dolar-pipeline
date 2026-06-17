from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_event(log_path: Path, event: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n")


def print_event(event: dict[str, Any]) -> None:
    print(json.dumps(event, sort_keys=True, ensure_ascii=True))

