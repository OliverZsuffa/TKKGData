"""Conservative classification for known Spotify episode release layouts."""
from __future__ import annotations
import re
from typing import Any

PART_RE = re.compile(r"\b(?:teil|part)\s*0*(\d+)\b", re.IGNORECASE)
EXTRA_PATTERNS = (
    (re.compile(r"\binhaltsangabe\b", re.I), "summary"),
    (re.compile(r"\banfangssong\b", re.I), "opening_song"),
    (re.compile(r"\btkkg\s*titelsong\b|\btitelsong\b", re.I), "opening_song"),
    (re.compile(r"\bschlußsong\b|\bschlusssong\b|\bschluss song\b", re.I), "closing_song"),
    (re.compile(r"\boutro\b", re.I), "outro"),
)

def classify_track(track: dict[str, Any]) -> dict[str, Any]:
    result = dict(track)
    name = str(track.get("name") or "")
    for pattern, kind in EXTRA_PATTERNS:
        if pattern.search(name):
            result["classification"] = kind
            return result
    match = PART_RE.search(name)
    if match:
        result["classification"] = "episode_part"
        result["part_number"] = int(match.group(1))
    else:
        result["classification"] = "unknown"
    return result

def validate_episode_parts(tracks: list[dict[str, Any]], profile: str = "standard") -> dict[str, Any]:
    classified = [classify_track(track) for track in tracks]
    parts = [t for t in classified if t["classification"] == "episode_part"]
    extras = [t for t in classified if t["classification"] not in ("episode_part", "unknown")]
    unknown = [t for t in classified if t["classification"] == "unknown"]
    if profile == "two_disc_duplicated_numbering":
        discs = sorted({int(t.get("disc_number") or 1) for t in parts})
        logical = []
        for disc in discs:
            disc_parts = sorted(
                (t for t in parts if int(t.get("disc_number") or 1) == disc),
                key=lambda t: int(t["part_number"]),
            )
            numbers = [t["part_number"] for t in disc_parts]
            if numbers != list(range(1, len(numbers) + 1)):
                return {"valid": False, "parts": [], "extras": extras, "unknown": unknown, "errors": [f"Disc {disc}: numbering is not continuous from 1"]}
            logical.extend(disc_parts)
        parts = logical
    else:
        parts.sort(key=lambda t: int(t["part_number"]))
        numbers = [t["part_number"] for t in parts]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            return {"valid": False, "parts": [], "extras": extras, "unknown": unknown, "errors": ["Part numbering is not continuous from 1"]}
    return {"valid": bool(parts), "parts": parts, "extras": extras, "unknown": unknown, "errors": [] if parts else ["No episode parts identified"]}
