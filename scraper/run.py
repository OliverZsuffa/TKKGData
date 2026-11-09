from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scraper.export import write_catalogue
from scraper.http import SourceAccessError, SourceClient
from scraper.merge import merge_records
from scraper.sources.archive import discover_archive_episodes, parse_archive_episode
from scraper.sources.official import SUPPLEMENTAL_DETAIL_URLS, discover_official_episodes
from scraper.validate import find_number_gaps, listening_link_coverage, validate_catalogue


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORT_PATH = DATA_DIR / "scrape-report.json"
HISTORICAL_INDEX_LATEST = 217


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    client = SourceClient()
    report = {
        "started_at": now,
        "sources": {},
        "warnings": [],
        "conflicts": [],
        "gaps": [],
        "episode_count": 0,
        "validation_errors": [],
        "success": False,
    }
    try:
        archive_entries = discover_archive_episodes(client)
        report["sources"]["archive_index_entries"] = len(archive_entries)
        report["sources"]["archive_index_max_number"] = max((entry["number"] for entry in archive_entries), default=0)
        archive_records = []
        for entry in archive_entries:
            try:
                if entry["number"] <= 206 and "serie/folge-" in entry["source_url"]:
                    archive_records.append(parse_archive_episode(client, entry))
                elif entry["number"] >= 207 and "audio.tkkg-site.de" in entry["source_url"]:
                    # Do not fetch or parse these posts: robots.txt on this
                    # subdomain has previously returned HTTP 403. The official
                    # catalogue is the permitted source for episodes 207–217.
                    if not any(isinstance(warning, dict) and warning.get("source") == "audio.tkkg-site.de" for warning in report["warnings"]):
                        report["warnings"].append({
                            "source": "audio.tkkg-site.de",
                            "numbers": [item["number"] for item in archive_entries if "audio.tkkg-site.de" in item.get("source_url", "")],
                            "stage": "robots",
                            "error": "Post fetching skipped because robots.txt access was previously denied with HTTP 403.",
                            "note": "These episodes are covered by the official catalogue. Access restrictions were not bypassed.",
                        })
                    continue
            except SourceAccessError as exc:
                source_url = entry.get("source_url", "")
                if "audio.tkkg-site.de" in source_url:
                    if not any(isinstance(warning, dict) and warning.get("source") == "audio.tkkg-site.de" for warning in report["warnings"]):
                        audio_numbers = [
                            item["number"] for item in archive_entries
                            if "audio.tkkg-site.de" in item.get("source_url", "")
                        ]
                        report["warnings"].append({
                            "source": "audio.tkkg-site.de",
                            "numbers": audio_numbers,
                            "stage": "robots" if "robots.txt" in str(exc) else "fetch",
                            "error": str(exc),
                            "note": "These episodes are covered by the official catalogue. Access controls were not bypassed.",
                        })
                else:
                    report["warnings"].append({
                        "source": "archive",
                        "number": entry.get("number"),
                        "title": entry.get("title"),
                        "source_url": source_url,
                        "stage": "fetch",
                        "error": str(exc),
                    })

        official_diagnostics: list[dict] = []
        official_records = discover_official_episodes(client, diagnostics=official_diagnostics)
        report["sources"]["official_records"] = len(official_records)
        report["sources"]["official_detail_fallback_records"] = sum(
            1 for item in official_records
            if any(source.get("url") in SUPPLEMENTAL_DETAIL_URLS.values() for source in item.get("sources", []))
        )
        report["sources"]["official_max_number"] = max((item["number"] for item in official_records), default=0)
        report["sources"]["official_rejected_records"] = official_diagnostics
        report["sources"]["official_rejected_count"] = len(official_diagnostics)
        report["sources"]["archive_detail_records"] = len(archive_records)

        archive_records.sort(key=lambda item: item["number"])
        official_records.sort(key=lambda item: item["number"])
        combined = archive_records + official_records
        episodes, conflicts = merge_records(combined)
        report["conflicts"] = conflicts
        report["gaps"] = find_number_gaps(episodes)
        report["episode_count"] = len(episodes)
        report["listening_link_coverage"] = listening_link_coverage(episodes)

        archive_max = report["sources"]["archive_index_max_number"]
        official_max = report["sources"]["official_max_number"]
        if archive_max < HISTORICAL_INDEX_LATEST:
            raise RuntimeError(f"Historical archive coverage unexpectedly ends at episode {archive_max}.")
        if official_max <= archive_max:
            raise RuntimeError(f"Official catalogue did not supply episodes beyond the archive index (max {official_max}).")
        if len(episodes) < HISTORICAL_INDEX_LATEST + 1:
            raise RuntimeError(f"Only {len(episodes)} episodes discovered; refusing to publish a suspiciously small catalogue.")
        if report["gaps"]:
            raise RuntimeError(f"Unexplained numbering gaps detected: {report['gaps']}. Refusing to publish an incomplete catalogue.")

        for episode in episodes:
            episode["last_checked"] = now
            for source in episode["sources"]:
                source.setdefault("retrieved_at", now)

        errors = validate_catalogue(episodes)
        report["validation_errors"] = errors
        if errors:
            raise RuntimeError(f"Catalogue schema validation failed with {len(errors)} error(s).")
        if conflicts:
            report["warnings"].append(f"Conflicting titles detected for {len(conflicts)} episode number(s); first source value retained.")

        write_catalogue(episodes, DATA_DIR)
        report["success"] = True
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Published {len(episodes)} episode records. Conflicts: {len(conflicts)}.")
        return 0
    except Exception as exc:
        report["fatal_error"] = str(exc)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Catalogue refresh failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
