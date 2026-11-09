from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "number", "series", "title", "synopsis", "cover_url", "release_date", "release_year",
    "physical_releases", "tracks", "cast", "credits", "ratings", "sources", "listening_links", "audio_release", "last_checked",
]


def write_catalogue(episodes: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "episodes.json"
    csv_path = output_dir / "episodes.csv"
    json_path.write_text(json.dumps(episodes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for episode in episodes:
            row = dict(episode)
            for field in CSV_FIELDS:
                if isinstance(row.get(field), (list, dict)):
                    row[field] = json.dumps(row[field], ensure_ascii=False)
            writer.writerow(row)

    metadata = {
        "schema_version": "1.0.0",
        "dataset_version": datetime.now(timezone.utc).isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "episode_count": len(episodes),
        "series": sorted({str(item.get("series", "TKKG")) for item in episodes}),
        "data_file": "episodes.json",
    }
    (output_dir / "dataset-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
    )
