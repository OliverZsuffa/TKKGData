from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any

from scraper.validate import validate_catalogue


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "data" / "episodes.json"
CSV_PATH = ROOT / "data" / "episodes.csv"


def _remove_pairings(episodes: list[dict[str, Any]]) -> int:
    removed = 0
    for episode in episodes:
        release = episode.get("audio_release") or {}
        youtube = release.get("youtube_music") or {}
        for track in youtube.get("tracks", []):
            if "legacy_pairing" in track:
                del track["legacy_pairing"]
                removed += 1
    return removed


def _clean_csv(content: str) -> tuple[str, int, int]:
    import io

    source = io.StringIO(content, newline="")
    reader = csv.DictReader(source)
    if not reader.fieldnames or "audio_release" not in reader.fieldnames:
        raise ValueError("episodes.csv has no audio_release column")

    rows = list(reader)
    removed = 0
    for row in rows:
        value = row.get("audio_release")
        if not value:
            continue
        release = json.loads(value)
        youtube = release.get("youtube_music") or {}
        for track in youtube.get("tracks", []):
            if "legacy_pairing" in track:
                del track["legacy_pairing"]
                removed += 1
        row["audio_release"] = json.dumps(release, ensure_ascii=False)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=reader.fieldnames,
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue(), removed, len(rows)


def _write_atomic(path: Path, content: str, encoding: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w",
        encoding=encoding,
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove redundant historical Spotify pairings from YouTube Music tracks."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the cleaned JSON and CSV files. Without this flag, only report the changes.",
    )
    args = parser.parse_args()

    episodes = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    removed_json = _remove_pairings(episodes)
    if removed_json == 0:
        print("No legacy_pairing fields found in episodes.json.")
        return 0

    validation_errors = validate_catalogue(episodes)
    if validation_errors:
        raise ValueError(
            "Cleaned episode data failed schema validation:\n"
            + "\n".join(validation_errors[:20])
        )

    csv_original = CSV_PATH.read_text(encoding="utf-8-sig")
    csv_cleaned, removed_csv, csv_rows = _clean_csv(csv_original)
    if removed_json != removed_csv:
        raise ValueError(
            f"JSON and CSV removal counts differ: {removed_json} versus {removed_csv}"
        )
    if len(episodes) != csv_rows:
        raise ValueError(
            f"JSON and CSV episode counts differ: {len(episodes)} versus {csv_rows}"
        )

    print(f"Found {removed_json} redundant fields in each export.")
    print(f"Validated {len(episodes)} episodes against the current JSON schema.")
    if not args.write:
        print("Dry run only. Re-run with --write to update both files.")
        return 0

    json_cleaned = json.dumps(episodes, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(JSON_PATH, json_cleaned, "utf-8")
    _write_atomic(CSV_PATH, csv_cleaned, "utf-8-sig")
    print("Updated data/episodes.json and data/episodes.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
