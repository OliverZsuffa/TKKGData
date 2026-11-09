from __future__ import annotations

import json
import re
from urllib.parse import urlparse
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
