from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def get_usage_file() -> Path:
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".autovideo-local"
    folder = base / "AutoVideoLocal"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path.home() / ".autovideo-local"
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            return folder / "edge_tts_usage.json"
    return folder / "edge_tts_usage.json"


def _read_data() -> dict[str, Any]:
    path = get_usage_file()
    if not path.exists():
        return {"last_request_epoch": None, "days": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid usage data")
        if not isinstance(data.get("days"), dict):
            data["days"] = {}
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        # A damaged counter must not prevent the user from creating a video.
        return {"last_request_epoch": None, "days": {}}


def _write_data(data: dict[str, Any]) -> None:
    path = get_usage_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="edge_tts_usage_", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    finally:
        try:
            if os.path.exists(temp_name):
                os.remove(temp_name)
        except OSError:
            pass


def get_last_request_epoch() -> float | None:
    with _LOCK:
        value = _read_data().get("last_request_epoch")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def record_request(character_count: int) -> None:
    now = time.time()
    local_day = datetime.now().astimezone().date().isoformat()

    with _LOCK:
        data = _read_data()
        days = data.setdefault("days", {})
        today = days.setdefault(local_day, {"requests": 0, "characters": 0})
        today["requests"] = int(today.get("requests", 0)) + 1
        today["characters"] = int(today.get("characters", 0)) + max(
            0, int(character_count)
        )
        data["last_request_epoch"] = now

        # Keep only the latest 60 daily counters.
        for day in sorted(days)[:-60]:
            days.pop(day, None)

        try:
            _write_data(data)
        except OSError:
            # Usage tracking must never block voice generation.
            pass


def get_usage_summary() -> dict[str, int]:
    local_day = datetime.now().astimezone().date().isoformat()
    with _LOCK:
        data = _read_data()
        today = data.get("days", {}).get(local_day, {})
        return {
            "requests": int(today.get("requests", 0)),
            "characters": int(today.get("characters", 0)),
        }