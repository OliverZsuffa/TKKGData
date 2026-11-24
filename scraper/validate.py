from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def validate_catalogue(episodes: list[dict], schema_path: Path | None = None) -> list[str]:
    schema_file = schema_path or ROOT / "schemas" / "episode.schema.json"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    seen: dict[int, str] = {}
    for index, episode in enumerate(episodes):
        for error in validator.iter_errors(episode):
            errors.append(f"episode index {index}: {error.message}")
        for release_index, release in enumerate(episode.get("physical_releases", [])):
            for field in ("medium", "label", "ean", "release_date"):
                value = release.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                if value.strip().casefold() in {"medium:", "label:", "ean:", "erscheinungstermin:"}:
                    errors.append(
                        f"episode {episode.get('number')} physical release {release_index}: "
                        f"{field} contains a field label instead of a value"
                    )
            ean = release.get("ean")
            if isinstance(ean, str) and ean.strip() and not re.search(r"\d{8,14}", ean):
                errors.append(
                    f"episode {episode.get('number')} physical release {release_index}: "
                    "EAN contains no plausible 8–14 digit identifier"
                )

        audio_release = episode.get("audio_release")
        if isinstance(audio_release, dict):
            if audio_release.get("schema_version") != 2:
                errors.append(f"episode {episode.get('number')}: unsupported audio_release schema version")
            verification = audio_release.get("verification") or {}
            for provider_name in ("spotify", "youtube_music"):
                provider = audio_release.get(provider_name)
                provider_verification = verification.get(provider_name) or {}
                if provider is None:
                    if provider_verification.get("status") == "verified":
                        errors.append(f"episode {episode.get('number')}: {provider_name} is marked verified but has no release data")
                    continue
                if not isinstance(provider, dict):
                    errors.append(f"episode {episode.get('number')}: {provider_name} release must be an object or null")
                    continue
                tracks = provider.get("tracks", [])
                if not isinstance(tracks, list) or provider.get("track_count") != len(tracks):
                    errors.append(f"episode {episode.get('number')}: {provider_name} track count does not match its own track list")
                    continue
                if provider_verification.get("status") == "verified" and provider_verification.get("verified_track_count") != len(tracks):
                    errors.append(f"episode {episode.get('number')}: {provider_name} verified track count does not match its own list")
                if provider_name == "spotify":
                    album = provider.get("album") or {}
                    album_id = album.get("album_id")
                    album_path_id = urlparse(str(album.get("url", ""))).path.rstrip("/").split("/")[-1]
                    if album_id != album_path_id:
                        errors.append(f"episode {episode.get('number')}: Spotify album ID does not match its URL")
                    positions = set()
                    previous = None
                    for track_index, track in enumerate(tracks):
                        if not isinstance(track, dict):
                            continue
                        track_id = track.get("track_id")
                        track_path_id = urlparse(str(track.get("url", ""))).path.rstrip("/").split("/")[-1]
                        if track_id != track_path_id:
                            errors.append(f"episode {episode.get('number')} Spotify track {track_index + 1}: track ID does not match its URL")
                        position = (int(track.get("disc_number") or 1), int(track.get("track_number") or 0))
                        if position in positions or (previous is not None and position < previous):
                            errors.append(f"episode {episode.get('number')} Spotify track order contains duplicate or decreasing album positions")
                        positions.add(position)
                        previous = position
                else:
                    playlist = provider.get("playlist")
                    if isinstance(playlist, dict):
                        ytm_id = playlist.get("playlist_id")
                        ytm_query_id = parse_qs(urlparse(str(playlist.get("url", ""))).query).get("list", [None])[0]
                        if ytm_id != ytm_query_id:
                            errors.append(f"episode {episode.get('number')}: YouTube Music playlist ID does not match its URL")
                        if playlist.get("track_count") != len(tracks):
                            errors.append(f"episode {episode.get('number')}: YouTube Music playlist count does not match its own track list")
                    album = provider.get("album")
                    if isinstance(album, dict):
                        browse_id = album.get("browse_id")
                        browse_path_id = urlparse(str(album.get("url", ""))).path.rstrip("/").split("/")[-1]
                        if browse_id != browse_path_id:
                            errors.append(f"episode {episode.get('number')}: YouTube Music album browse ID does not match its URL")
                        if album.get("track_count") != len(tracks):
                            errors.append(f"episode {episode.get('number')}: YouTube Music album count does not match its own track list")
                    for track_index, track in enumerate(tracks):
                        if not isinstance(track, dict):
                            continue
                        video_id = track.get("video_id")
                        query_id = parse_qs(urlparse(str(track.get("url", ""))).query).get("v", [None])[0]
                        if video_id != query_id:
                            errors.append(f"episode {episode.get('number')} YouTube Music track {track_index + 1}: video ID does not match its URL")
                        if track.get("track_number") != track_index + 1:
                            errors.append(f"episode {episode.get('number')} YouTube Music track order is not contiguous")
            if verification.get("status") == "verified":
                for provider_name in ("spotify", "youtube_music"):
                    if (verification.get(provider_name) or {}).get("status") != "verified":
                        errors.append(f"episode {episode.get('number')}: combined audio release is verified but {provider_name} is not")

        number = episode.get("number")
        title = episode.get("title")
        if isinstance(number, int):
            if number in seen:
                errors.append(f"duplicate episode number {number}: {seen[number]!r} and {title!r}")
            else:
                seen[number] = str(title)
    return errors


def find_number_gaps(episodes: list[dict]) -> list[int]:
    numbers = sorted({episode["number"] for episode in episodes if isinstance(episode.get("number"), int)})
    if not numbers:
        return []
    return sorted(set(range(1, numbers[-1] + 1)) - set(numbers))


def listening_link_coverage(episodes: list[dict]) -> dict:
    """Summarise verified catalogue links and list episodes without an official hub."""
    by_service: dict[str, int] = {}
    by_type: dict[str, int] = {}
    without_links: list[dict] = []
    invalid_links: list[dict] = []
    total_links = 0
    direct_links = 0
    fallback_links = 0
    episodes_with_links = 0

    for episode in episodes:
        links = episode.get("listening_links", [])
        if not links:
            without_links.append({"number": episode.get("number"), "title": episode.get("title")})
            continue
        episodes_with_links += 1
        for link in links:
            total_links += 1
            service = str(link.get("service", "unknown"))
            link_type = str(link.get("link_type", "unknown"))
            by_service[service] = by_service.get(service, 0) + 1
            by_type[link_type] = by_type.get(link_type, 0) + 1
            if link_type in {"episode", "release"}:
                direct_links += 1
            else:
                fallback_links += 1
            try:
                parsed = urlparse(link.get("url", ""))
                valid_url = parsed.scheme == "https" and bool(parsed.netloc)
                if service == "official":
                    valid_url = valid_url and parsed.hostname == "tkkg.lnk.to" and parsed.path not in {"", "/alle-hoerspiele"}
            except (TypeError, ValueError):
                valid_url = False
            if not valid_url:
                invalid_links.append({
                    "number": episode.get("number"),
                    "title": episode.get("title"),
                    "service": service,
                    "url": link.get("url"),
                    "reason": "Destination is not a valid HTTPS URL for its declared service.",
                })

    return {
        "episode_count": len(episodes),
        "episodes_with_listening_links": episodes_with_links,
        "episodes_without_listening_links": without_links,
        "link_count": total_links,
        "links_by_service": by_service,
        "links_by_type": by_type,
        "direct_episode_or_release_link_count": direct_links,
        "hub_or_fallback_link_count": fallback_links,
        "invalid_links": invalid_links,
    }
