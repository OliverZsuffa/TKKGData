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
    run_started_at = datetime.now(timezone.utc).isoformat()
    if args.max_parallel < 1 or args.max_parallel > 8:
        raise ValueError("Maximum parallel batches must be between 1 and 8.")
    episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
    selected = select_episodes(
        episodes, episode=args.episode, start_episode=args.start_episode,
        end_episode=args.end_episode, limit=args.limit,
    )
    if args.playlist_id and len(selected) != 1:
        raise ValueError("--playlist-id requires exactly one selected episode.")
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
            handle.write(f"max_parallel={args.max_parallel}\n")
            handle.write(f"run_started_at={run_started_at}\n")
    print(json.dumps({
        "selected_count": len(selected),
        "batch_count": len(batches),
        "batch_size": args.batch_size,
        "max_parallel": args.max_parallel,
        "run_started_at": run_started_at,
        "matrix": matrix,
    }, indent=2))
    return 0


def aggregate(
    catalogue_path: Path, reports_dir: Path, matrix_json: str, *, write: bool,
    discovery_result: str, max_parallel: int = 4,
    run_started_at: str | None = None,
) -> dict[str, Any]:
    aggregate_started = datetime.now(timezone.utc)
    if max_parallel < 1 or max_parallel > 8:
        raise ValueError("Maximum parallel batches must be between 1 and 8.")
    workflow_started = aggregate_started
    if run_started_at:
        try:
            workflow_started = datetime.fromisoformat(run_started_at.replace("Z", "+00:00"))
            if workflow_started.tzinfo is None:
                workflow_started = workflow_started.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError(f"Invalid workflow start timestamp: {run_started_at}") from exc
    matrix = json.loads(matrix_json)
    batches = matrix.get("include") if isinstance(matrix, dict) else None
    if not isinstance(batches, list) or not batches:
        raise ValueError("The expected batch matrix is empty or malformed.")
    if any(not isinstance(item, dict) for item in batches):
        raise ValueError("Every batch matrix entry must be an object.")
    batch_ids = [int(item["batch"]) for item in batches]
    if len(batch_ids) != len(set(batch_ids)):
        raise ValueError("The batch matrix contains duplicate batch IDs.")
    selected_numbers = [
        int(number)
        for item in batches
        for number in item.get("episodes", [])
    ]
    if not selected_numbers or any(number < 1 for number in selected_numbers):
        raise ValueError("The batch matrix must contain positive episode numbers.")
    if len(selected_numbers) != len(set(selected_numbers)):
        raise ValueError("The batch matrix assigns an episode more than once.")
    combined: dict[str, Any] = {
        "started_at": workflow_started.isoformat(),
        "aggregate_started_at": aggregate_started.isoformat(),
        "mode": "write" if write else "dry_run",
        "max_parallel": max_parallel,
        "expected_batches": len(batches),
        "batches": [],
        "verified": [],
        "failures": [],
        "preserved_existing": [],
        "missing_reports": [],
        "catalogue_updated": False,
        "expected_episode_count": len(selected_numbers),
    }
    reports: dict[int, dict[str, Any]] = {}
    for batch in batches:
        index = int(batch["batch"])
        path = reports_dir / f"batch-{index}.json"
        if not path.is_file():
            combined["missing_reports"].append(path.name)
            continue
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

    if discovery_result != "success" or combined["missing_reports"]:
        reasons = []
        if discovery_result != "success":
            reasons.append(f"Discovery matrix job result was {discovery_result}")
        if combined["missing_reports"]:
            reasons.append("Missing required reports: " + ", ".join(combined["missing_reports"]))
        combined["publication_blocked"] = "; ".join(reasons) + ". No catalogue changes were published."
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
    finished = datetime.now(timezone.utc)
    combined["finished_at"] = finished.isoformat()
    combined["duration_seconds"] = round((finished - workflow_started).total_seconds(), 2)
    combined["episode_processing_seconds"] = round(sum(
        float(item.get("timings", {}).get("total_seconds", 0))
        for item in combined["verified"] + combined["failures"]
    ), 2)
    combined["selected_count"] = combined["expected_episode_count"]
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
    prepare_parser.add_argument("--playlist-id")
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    aggregate_parser.add_argument("--reports-dir", type=Path, required=True)
    aggregate_parser.add_argument("--matrix-json", required=True)
    aggregate_parser.add_argument("--write", action="store_true")
    aggregate_parser.add_argument("--discovery-result", default="success")
    aggregate_parser.add_argument("--max-parallel", type=int, default=4)
    aggregate_parser.add_argument("--run-started-at")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            if args.limit < 1 or args.limit > 20:
                raise ValueError("--limit must be between 1 and 20.")
            return prepare(args)
        report = aggregate(
            args.catalogue, args.reports_dir, args.matrix_json,
            write=args.write, discovery_result=args.discovery_result,
            max_parallel=args.max_parallel, run_started_at=args.run_started_at,
        )
        report_path = args.reports_dir / "combined-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary = {
            "selected": report["selected_count"],
            "verified": report["verified_count"],
            "unresolved": report["unresolved_count"],
            "batches": report["expected_batches"],
            "max_parallel": report["max_parallel"],
            "duration_seconds": report["duration_seconds"],
            "episode_processing_seconds": report["episode_processing_seconds"],
            "preserved_existing": len(report["preserved_existing"]),
            "catalogue_updated": report["catalogue_updated"],
            "publication_blocked": report.get("publication_blocked"),
        }
        print(json.dumps(summary, indent=2))
        summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
        if summary_path:
            publication = report.get("publication_blocked") or (
                "Published verified mappings." if report["catalogue_updated"]
                else "Dry run only. No catalogue changes were published."
            )
            summary_path.write_text(
                "\n".join([
                    "## TKKG audio batch discovery",
                    "",
                    f"- Selected: **{report['selected_count']}**",
                    f"- Verified: **{report['verified_count']}**",
                    f"- Unresolved: **{report['unresolved_count']}**",
                    f"- Batches: **{report['expected_batches']}**",
                    f"- Maximum parallel batches: **{report['max_parallel']}**",
                    f"- Wall clock runtime: **{report['duration_seconds']} s**",
                    f"- Sum of episode processing time: **{report['episode_processing_seconds']} s**",
                    f"- Existing verified mappings preserved: **{len(report['preserved_existing'])}**",
                    f"- Publication: {publication}",
                    "",
                    "| Batch | Episodes | Verified | Unresolved |",
                    "|---:|---:|---:|---:|",
                    *[
                        f"| {item['batch']} | {len(item['episodes'])} | {item['verified_count']} | {item['unresolved_count']} |"
                        for item in report["batches"]
                    ],
                ]) + "\n",
                encoding="utf-8",
            )
        if report.get("publication_blocked"):
            return 1
        return 0
    except Exception as exc:
        print(f"Audio batch {args.command} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
