"""Conservative classification for known Spotify episode release layouts."""
from __future__ import annotations
import re
from typing import Any

PART_RE = re.compile(r"\b(?:teil|part)\s*0*(\d+)\b", re.IGNORECASE)
EXTRA_PATTERNS = (
    (re.compile(r"\binhaltsangabe\b", re.I), "summary"),
    (re.compile(r"\bintro\b|\bintroduction\b|\beinleitung\b|\bvorspann\b", re.I), "intro"),
    (re.compile(r"\banfangssong\b", re.I), "opening_song"),
    (re.compile(r"\btkkg\s*titelsong\b|\btitelsong\b", re.I), "opening_song"),
    (re.compile(r"\bschlußsong\b|\bschlusssong\b|\bschluss song\b|\boutsong\b", re.I), "closing_song"),
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


def validate_selected_track_positions(tracks: list[dict[str, Any]]) -> list[str]:
    """Validate selected tracks without assuming episode parts occupy adjacent album slots.

    Extras and shared tracks can legitimately sit between episode parts in a release.
    When part labels are present, their logical numbering is authoritative. For
    unlabelled multi-track selections, retain the conservative contiguous-position rule.
    """
    if not tracks:
        return ["No selected tracks"]
    positions = [
        (int(track.get("disc_number") or 1), int(track.get("track_number") or 0))
        for track in tracks
    ]
    if any(track_number < 1 for _, track_number in positions):
        return ["Selected tracks have invalid positions"]
    if len(set(positions)) != len(positions):
        return ["Selected tracks have duplicate positions"]

    numbered_parts: list[int] = []
    unnumbered = 0
    for track in tracks:
        match = PART_RE.search(str(track.get("name") or ""))
        if match:
            numbered_parts.append(int(match.group(1)))
        else:
            unnumbered += 1

    if numbered_parts:
        if sorted(numbered_parts) != list(range(1, len(numbered_parts) + 1)):
            return ["Episode part numbering is not continuous from 1"]
        # Recognised shared tracks may be separated from the numbered parts in
        # the album. Their association is established by the selector, while
        # logical part numbering and unique album positions remain mandatory.
        return []
    if len(tracks) > 1:
        ordered_positions = sorted(positions)
        if any(
            current[0] != previous[0] or current[1] != previous[1] + 1
            for previous, current in zip(ordered_positions, ordered_positions[1:])
        ):
            return ["Selected tracks are not contiguous and have no complete part numbering"]
    return []

def validate_episode_parts(tracks: list[dict[str, Any]], profile: str = "standard") -> dict[str, Any]:
    positions = [
        (int(track.get("disc_number") or 1), int(track.get("track_number") or 0))
        for track in tracks
    ]
    if any(track_number < 1 for _, track_number in positions):
        return {"valid": False, "parts": [], "extras": [], "tracks": [], "unknown": [], "errors": ["Album contains invalid track positions"]}
    if len(set(positions)) != len(positions):
        return {"valid": False, "parts": [], "extras": [], "tracks": [], "unknown": [], "errors": ["Album contains duplicate track positions"]}
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
            if len(set(numbers)) != len(numbers) or numbers != list(range(1, len(numbers) + 1)):
                return {"valid": False, "parts": [], "extras": extras, "unknown": unknown, "errors": [f"Disc {disc}: numbering is not continuous from 1"]}
            logical.extend(disc_parts)
        parts = logical
    else:
        parts.sort(key=lambda t: int(t["part_number"]))
        numbers = [t["part_number"] for t in parts]
        if len(set(numbers)) != len(numbers) or (numbers and numbers != list(range(1, len(numbers) + 1))):
            return {"valid": False, "parts": [], "extras": extras, "unknown": unknown, "errors": ["Part numbering is not continuous from 1"]}
    ordered_tracks = sorted(
        [*parts, *extras],
        key=lambda track: (
            int(track.get("disc_number") or 1),
            int(track.get("track_number") or 0),
        ),
    )
    return {
        "valid": bool(parts),
        "parts": parts,
        "extras": extras,
        "tracks": ordered_tracks,
        "unknown": unknown,
        "errors": [] if parts else ["No episode parts identified"],
    }


def select_episode_release_tracks(
    album_tracks: list[dict[str, Any]],
    selected_parts: list[dict[str, Any]],
    profile: str = "standard",
) -> list[dict[str, Any]]:
    """Keep episode parts and their structurally adjacent shared tracks in album order.

    For known shared-title-song releases, the common opening song is also retained
    even when it appears before the episode's contiguous track block.
    """
    if not selected_parts:
        return []

    def position(track: dict[str, Any]) -> tuple[int, int]:
        return (
            int(track.get("disc_number") or 1),
            int(track.get("track_number") or 0),
        )

    ordered = sorted(album_tracks, key=position)
    classified = [classify_track(track) for track in ordered]
    selected_keys = {
        (
            str(track.get("song_id") or ""),
            position(track),
        )
        for track in selected_parts
    }
    selected_indices = {
        index
        for index, track in enumerate(ordered)
        if (str(track.get("song_id") or ""), position(track)) in selected_keys
    }
    if not selected_indices:
        return []

    first = min(selected_indices)
    last = max(selected_indices)
    included = set(selected_indices)
    extra_kinds = {"summary", "intro", "opening_song", "outro", "closing_song"}

    for index in range(first, last + 1):
        if classified[index].get("classification") in extra_kinds:
            included.add(index)

    for direction, start in ((-1, first - 1), (1, last + 1)):
        index = start
        while 0 <= index < len(ordered):
            if classified[index].get("classification") not in extra_kinds:
                break
            included.add(index)
            index += direction

    if profile == "shared_title_song":
        included.update(
            index
            for index, track in enumerate(classified)
            if track.get("classification") == "opening_song"
        )

    return [ordered[index] for index in sorted(included, key=lambda item: position(ordered[item]))]
