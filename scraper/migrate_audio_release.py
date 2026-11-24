from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "data" / "episodes.json"
DEFAULT_OVERRIDES = ROOT / "data" / "spotify_structure_overrides.json"


def _merge_unique(existing: list[str], additions: list[str], canonical_title: str) -> list[str]:
    result: list[str] = []
    seen = {canonical_title.strip().casefold()}
    for value in [*existing, *additions]:
        if not isinstance(value, str) or not value.strip():
            continue
        cleaned = value.strip()
        key = cleaned.casefold()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _migrate_release(episode: dict[str, Any], migrated_at: str) -> dict[str, Any]:
    old = episode.get("audio_release")
    spotify = old.get("spotify") if isinstance(old, dict) else None
    youtube = old.get("youtube_music") if isinstance(old, dict) else None
    verification = old.get("verification") if isinstance(old, dict) else None
    if not all(isinstance(value, dict) for value in (spotify, youtube, verification)):
        raise ValueError(f"Episode {episode.get('number')}: malformed legacy audio_release")
    old_tracks = youtube.get("tracks")
    if not isinstance(old_tracks, list) or not old_tracks:
        raise ValueError(f"Episode {episode.get('number')}: legacy YouTube Music track list is empty")

    spotify_tracks: list[dict[str, Any]] = []
    youtube_tracks: list[dict[str, Any]] = []
    for index, source in enumerate(old_tracks, start=1):
        if not isinstance(source, dict):
            raise ValueError(f"Episode {episode.get('number')}: legacy track {index} is not an object")
        track_number = source.get("track_number", index)
        spotify_id = source.get("spotify_track_id")
        spotify_url = source.get("spotify_track_url")
        spotify_title = source.get("spotify_title")
        video_id = source.get("video_id")
        video_url = source.get("url")
        ytm_title = source.get("title")
        if not all(isinstance(value, str) and value.strip() for value in (
            spotify_id, spotify_url, spotify_title, video_id, video_url, ytm_title
        )):
            raise ValueError(
                f"Episode {episode.get('number')}: legacy track {index} lacks an ID, URL, or title; "
                "migration aborted to avoid dropping source data"
            )
        spotify_tracks.append({
            "track_number": track_number,
            "track_id": spotify_id,
            "url": spotify_url,
            "title": spotify_title,
        })
        youtube_track = {
            "track_number": track_number,
            "video_id": video_id,
            "url": video_url,
            "title": ytm_title,
            "artists": deepcopy(source.get("artists") or []),
            "album": source.get("album"),
            "duration_seconds": source.get("duration_seconds"),
            "match_score": source.get("match_score"),
            "match_evidence": deepcopy(source.get("match_evidence") or []),
            "legacy_pairing": {
                "spotify_track_id": spotify_id,
                "spotify_track_url": spotify_url,
                "spotify_title": spotify_title,
            },
        }
        youtube_tracks.append({key: value for key, value in youtube_track.items() if value is not None})

    if spotify.get("track_count") != len(spotify_tracks) or youtube.get("track_count") != len(youtube_tracks):
        raise ValueError(f"Episode {episode.get('number')}: declared source counts do not match source tracks")
    if verification.get("matched_track_count") not in (None, len(youtube_tracks)):
        raise ValueError(f"Episode {episode.get('number')}: legacy matched count does not match source tracks")

    status = verification.get("status", "partial")
    return {
        "schema_version": 2,
        "spotify": {
            "album": {
                "album_id": spotify["album_id"],
                "url": spotify["url"],
                "title": spotify["title"],
                "track_count": len(spotify_tracks),
                "source_query": spotify["source_query"],
            },
            "tracks": spotify_tracks,
            "track_count": len(spotify_tracks),
        },
        "youtube_music": {
            "album": None,
            "playlist": deepcopy(youtube.get("playlist")),
            "tracks": youtube_tracks,
            "track_count": len(youtube_tracks),
        },
        "verification": {
            "status": status,
            "verified_at": verification.get("verified_at"),
            "method": "migrated_from_legacy_verified_track_pairs",
            "spotify": {
                "status": "verified" if status == "verified" else "unverified",
                "verified_track_count": len(spotify_tracks) if status == "verified" else 0,
            },
            "youtube_music": {
                "status": "verified" if status == "verified" else "unverified",
                "verified_track_count": len(youtube_tracks) if status == "verified" else 0,
                "playlist_status": verification.get("playlist_status"),
                "playlist_error": verification.get("playlist_error"),
            },
            "migration": {
                "source_schema_version": 1,
                "migrated_at": migrated_at,
                "source_verification": deepcopy(verification),
            },
        },
    }


def migrate_catalogue(
    episodes: list[dict[str, Any]],
    overrides: dict[str, Any] | None = None,
    migrated_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    migrated_at = migrated_at or datetime.now(timezone.utc).isoformat()
    overrides = overrides or {}
    result = deepcopy(episodes)
    by_number = {str(item.get("number")): item for item in result}
    missing = sorted(set(overrides) - set(by_number), key=lambda value: int(value))
    if missing:
        raise ValueError(f"Override entries reference missing episodes: {missing}")

    report: dict[str, Any] = {
        "migrated_at": migrated_at,
        "episode_count": len(result),
        "migrated_episode_count": 0,
        "spotify_track_count": 0,
        "youtube_music_track_count": 0,
        "discovery_hint_episode_count": 0,
        "alternate_title_count": 0,
        "override_entry_count": len(overrides),
        "episodes": [],
    }

    for episode in result:
        number = str(episode.get("number"))
        override = overrides.get(number, {})
        if not isinstance(override, dict):
            raise ValueError(f"Episode {number}: malformed override entry")
        aliases = override.get("alternate_titles", [])
        if aliases:
            if not isinstance(aliases, list):
                raise ValueError(f"Episode {number}: alternate_titles must be a list")
            before = episode.get("alternate_titles") or []
            merged = _merge_unique(before, aliases, str(episode.get("title") or ""))
            report["alternate_title_count"] += len(merged) - len(before)
            if merged:
                episode["alternate_titles"] = merged

        hint = {
            key: value for key, value in {
                "preferred_album_id": override.get("album_id"),
                "release_profile": override.get("profile"),
                "expected_story_parts": override.get("expected_parts"),
            }.items() if value is not None
        }
        if hint:
            existing = episode.get("audio_discovery") or {}
            existing_spotify = existing.get("spotify") or {}
            for key, value in hint.items():
                if key in existing_spotify and existing_spotify[key] != value:
                    raise ValueError(f"Episode {number}: conflicting audio_discovery.spotify.{key}")
            episode["audio_discovery"] = {
                **existing,
                "spotify": {**existing_spotify, **hint},
            }
            report["discovery_hint_episode_count"] += 1

        old = episode.get("audio_release")
        if isinstance(old, dict) and old.get("schema_version") != 2:
            new_release = _migrate_release(episode, migrated_at)
            preferred = hint.get("preferred_album_id")
            if preferred and preferred != new_release["spotify"]["album"]["album_id"]:
                raise ValueError(f"Episode {number}: preferred album ID conflicts with verified release")
            episode["audio_release"] = new_release
            sp_count = new_release["spotify"]["track_count"]
            yt_count = new_release["youtube_music"]["track_count"]
            report["migrated_episode_count"] += 1
            report["spotify_track_count"] += sp_count
            report["youtube_music_track_count"] += yt_count
            report["episodes"].append({
                "number": episode.get("number"),
                "spotify_tracks": sp_count,
                "youtube_music_tracks": yt_count,
            })

    report["preservation_check"] = {
        "all_override_entries_mapped": True,
        "all_legacy_tracks_migrated": True,
    }
    return result, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate paired TKKG audio metadata to independent provider lists")
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--write", action="store_true", help="write the migrated catalogue and report")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "audio-migration-report.json")
    args = parser.parse_args()
    episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
    overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides.exists() else {}
    migrated, report = migrate_catalogue(episodes, overrides)
    if args.write:
        from scraper.export import write_catalogue
        from scraper.validate import validate_catalogue

        errors = validate_catalogue(migrated)
        if errors:
            raise SystemExit("Candidate migration failed catalogue validation:\\n" + "\\n".join(errors))

        related_paths = [
            args.catalogue,
            args.catalogue.with_name("episodes.csv"),
            args.catalogue.with_name("dataset-metadata.json"),
            args.overrides,
            args.report,
        ]
        with tempfile.TemporaryDirectory(prefix="tkkg_audio_migration_") as backup_dir:
            backup_root = Path(backup_dir)
            backups: dict[Path, Path] = {}
            for target in related_paths:
                if target.exists():
                    backup = backup_root / target.name
                    shutil.copy2(target, backup)
                    backups[target] = backup
            try:
                write_catalogue(migrated, args.catalogue.parent)
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\\n",
                    encoding="utf-8",
                )
                if args.overrides.exists():
                    args.overrides.unlink()
                final_episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
                final_errors = validate_catalogue(final_episodes)
                if final_errors:
                    raise RuntimeError("Written migration failed validation: " + "; ".join(final_errors[:10]))
            except Exception:
                for target in related_paths:
                    if target.exists():
                        target.unlink()
                for target, backup in backups.items():
                    shutil.copy2(backup, target)
                raise
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
