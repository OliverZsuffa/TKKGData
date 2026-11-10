from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scraper.audio_enrichment import audio_release_coverage
from scraper.export import write_catalogue
from scraper.validate import validate_catalogue


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "data" / "episodes.json"


def select_episodes(
    episodes: list[dict[str, Any]], *, episode: int | None = None,
    start_episode: int | None = None, end_episode: int | None = None,
    limit: int = 5,
) -> list[int]:
    available = sorted(
        int(item["number"]) for item in episodes
        if isinstance(item, dict) and isinstance(item.get("number"), int)
    )
    if episode is not None:
        if start_episode is not None or end_episode is not None:
            raise ValueError("Use either --episode or an episode range, not both.")
        requested = [episode]
    elif start_episode is not None or end_episode is not None:
        if start_episode is None or end_episode is None:
            raise ValueError("Both range bounds must be supplied.")
        if start_episode < 1 or end_episode < 1 or start_episode > end_episode:
            raise ValueError("Episode range must be positive and start must not exceed end.")
        requested = list(range(start_episode, end_episode + 1))
    else:
        missing = {
            int(item["number"]) for item in episodes
            if not (
                isinstance(item.get("audio_release"), dict)
                and item["audio_release"].get("verification", {}).get("status") == "verified"
            )
        }
        requested = sorted(missing, reverse=True)[:limit]
    if not requested:
        raise ValueError("No episodes were selected.")
    absent = sorted(set(requested) - set(available))
    if absent:
        raise ValueError(f"Requested episodes are not present in the catalogue: {absent}")
    return requested


def partition(items: list[int], batch_size: int) -> list[list[int]]:
    if batch_size < 1 or batch_size > 10:
        raise ValueError("Batch size must be between 1 and 10.")
    return [items[index:index + batch_size] for index in range(0, len(items), batch_size)]


def prepare(args: argparse.Namespace) -> int:
    if args.max_parallel < 1 or args.max_parallel > 8:
        raise ValueError("Maximum parallel batches must be between 1 and 8.")
    episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
    selected = select_episodes(
        episodes, episode=args.episode, start_episode=args.start_episode,
        end_episode=args.end_episode, limit=args.limit,
    )
    batches = partition(selected, args.batch_size)
    matrix = {"include": [
        {"batch": index, "episodes": numbers}
        for index, numbers in enumerate(batches)
    ]}
    encoded = json.dumps(matrix, separators=(",", ":"))
    output = Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None
    if output:
        with output.open("a", encoding="utf-8") as handle:
            handle.write(f"matrix={encoded}\n")
            handle.write(f"batch_count={len(batches)}\n")
            handle.write(f"selected_count={len(selected)}\n")
    print(json.dumps({
        "selected_count": len(selected),
        "batch_count": len(batches),
        "batch_size": args.batch_size,
        "max_parallel": args.max_parallel,
        "matrix": matrix,
    }, indent=2))
    return 0


def aggregate(
    catalogue_path: Path, reports_dir: Path, matrix_json: str, *, write: bool,
    discovery_result: str,
) -> dict[str, Any]:
    matrix = json.loads(matrix_json)
    batches = matrix.get("include") if isinstance(matrix, dict) else None
    if not isinstance(batches, list) or not batches:
        raise ValueError("The expected batch matrix is empty or malformed.")
    combined: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "write" if write else "dry_run",
        "expected_batches": len(batches),
        "batches": [],
        "verified": [],
        "failures": [],
        "preserved_existing": [],
        "catalogue_updated": False,
    }
    reports: dict[int, dict[str, Any]] = {}
    for batch in batches:
        index = int(batch["batch"])
        path = reports_dir / f"batch-{index}.json"
        if not path.is_file():
            raise RuntimeError(f"Required batch report is missing: {path.name}")
        report = json.loads(path.read_text(encoding="utf-8"))
        expected_numbers = sorted(int(value) for value in batch["episodes"])
        actual_numbers = sorted(int(value) for value in report.get("selected_numbers", []))
        if actual_numbers != expected_numbers or report.get("target_count") != len(expected_numbers):
            raise RuntimeError(
                f"Batch {index} report does not cover its assigned episodes. "
                f"Expected {expected_numbers}, received {actual_numbers}."
            )
        processed = sorted(
            [int(item["number"]) for item in report.get("verified", [])]
            + [int(item["number"]) for item in report.get("failures", [])]
        )
        if processed != expected_numbers:
            raise RuntimeError(f"Batch {index} report has missing or duplicate episode outcomes.")
        reports[index] = report
        combined["batches"].append({
            "batch": index,
            "episodes": expected_numbers,
            "verified_count": len(report.get("verified", [])),
            "unresolved_count": len(report.get("failures", [])),
        })
        combined["verified"].extend(report.get("verified", []))
        combined["failures"].extend(report.get("failures", []))

    if discovery_result != "success":
        combined["publication_blocked"] = (
            f"Discovery matrix job result was {discovery_result}; no catalogue changes were published."
        )
    else:
        episodes = json.loads(catalogue_path.read_text(encoding="utf-8"))
        by_number = {int(item["number"]): item for item in episodes}
        for result in combined["verified"]:
            number = int(result["number"])
            if number not in by_number:
                raise ValueError(f"Verified result references unknown episode {number}.")
            current = by_number[number].get("audio_release")
            existing_verified = (
                isinstance(current, dict)
                and current.get("verification", {}).get("status") == "verified"
            )
            if existing_verified:
                if current != result["audio_release"]:
                    combined["preserved_existing"].append({
                        "number": number,
                        "reason": "Existing verified mapping retained because the new result differs.",
                    })
                continue
            if write:
                by_number[number]["audio_release"] = deepcopy(result["audio_release"])
        errors = validate_catalogue(episodes)
        combined["validation_errors"] = errors
        if errors:
            raise RuntimeError(f"Full catalogue validation failed: {errors[:10]}")
        if write:
            write_catalogue(episodes, catalogue_path.parent)
            combined["catalogue_updated"] = True
            scrape_report_path = catalogue_path.parent / "scrape-report.json"
            try:
                scrape_report = json.loads(scrape_report_path.read_text(encoding="utf-8"))
                if not isinstance(scrape_report, dict):
                    scrape_report = {}
            except (OSError, json.JSONDecodeError):
                scrape_report = {}
            scrape_report["audio_release_coverage"] = audio_release_coverage(episodes)
            scrape_report["audio_enrichment"] = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "verified_count": len(combined["verified"]),
                "failure_count": len(combined["failures"]),
                "batch_count": len(batches),
            }
            scrape_report_path.write_text(
                json.dumps(scrape_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    combined["finished_at"] = datetime.now(timezone.utc).isoformat()
    combined["duration_seconds"] = sum(
        float(item.get("timings", {}).get("total_seconds", 0))
        for item in combined["verified"] + combined["failures"]
    )
    combined["selected_count"] = sum(len(item["episodes"]) for item in combined["batches"])
    combined["unresolved_count"] = len(combined["failures"])
    combined["verified_count"] = len(combined["verified"])
    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and aggregate parallel TKKG audio discovery batches.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    prepare_parser.add_argument("--episode", type=int)
    prepare_parser.add_argument("--start-episode", type=int)
    prepare_parser.add_argument("--end-episode", type=int)
    prepare_parser.add_argument("--limit", type=int, default=5)
    prepare_parser.add_argument("--batch-size", type=int, default=5)
    prepare_parser.add_argument("--max-parallel", type=int, default=4)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    aggregate_parser.add_argument("--reports-dir", type=Path, required=True)
    aggregate_parser.add_argument("--matrix-json", required=True)
    aggregate_parser.add_argument("--write", action="store_true")
    aggregate_parser.add_argument("--discovery-result", default="success")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            if args.limit < 1:
                raise ValueError("--limit must be positive.")
            return prepare(args)
        report = aggregate(
            args.catalogue, args.reports_dir, args.matrix_json,
            write=args.write, discovery_result=args.discovery_result,
        )
        report_path = args.reports_dir / "combined-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "selected": report["selected_count"],
            "verified": report["verified_count"],
            "unresolved": report["unresolved_count"],
            "preserved_existing": len(report["preserved_existing"]),
            "catalogue_updated": report["catalogue_updated"],
            "publication_blocked": report.get("publication_blocked"),
        }, indent=2))
        if report.get("publication_blocked"):
            return 1
        return 0
    except Exception as exc:
        print(f"Audio batch {args.command} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
