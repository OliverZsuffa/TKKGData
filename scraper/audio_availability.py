from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data" / "audio-unavailable.json"


def load_audio_unavailable(path: Path = DEFAULT_PATH) -> dict[int, dict[str, Any]]:
    """Return reviewed episodes that have no expected official digital music release."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("episodes"), dict):
        raise ValueError("Malformed audio-unavailable registry.")
    result: dict[int, dict[str, Any]] = {}
    for number, details in data["episodes"].items():
        if not str(number).isdigit() or not isinstance(details, dict):
            raise ValueError(f"Malformed audio-unavailable entry: {number!r}")
        result[int(number)] = details
    return result
