from __future__ import annotations

import argparse
import json
import os
import sys
import re
import tempfile
import time
import unicodedata
from copy import deepcopy
from functools import partial
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scraper.export import write_catalogue
from urllib.parse import parse_qs, urlencode, urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CATALOGUE_PATH = DATA_DIR / "episodes.json"
REPORT_PATH = DATA_DIR / "audio-enrichment-report.json"
SCRAPE_REPORT_PATH = DATA_DIR / "scrape-report.json"
YTM_BASE = "https://music.youtube.com/playlist?"
SPOTIFY_ALBUM_BASE = "https://open.spotify.com/album/"


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"^\s*tkkg\s+", "", value)
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _spotify_metadata_library() -> tuple[Any, Any]:
    """Load spotDL's metadata classes without invoking its downloader CLI."""
    try:
        from spotdl.types.album import Album
        from spotdl.types.song import Song
        from spotdl.utils.config import SPOTIFY_OPTIONS
        from spotdl.utils.spotify import SpotifyClient
    except ImportError as exc:
        raise RuntimeError(
            "spotDL metadata dependencies are missing. Install requirements-audio.txt."
        ) from exc

    if getattr(SpotifyClient, "_instance", None) is None:
        settings = dict(SPOTIFY_OPTIONS)
        settings.update({"no_cache": False, "max_retries": 2, "headless": True})
        SpotifyClient.init(**settings)
    return Song, Album


def _spotify_search_records(query: str) -> list[dict[str, Any]]:
    """Return multiple raw Spotify search candidates without downloading audio."""
    Song, _ = _spotify_metadata_library()
    try:
        payload = Song.search(query)
    except Exception as exc:
        raise RuntimeError(f"Spotify metadata lookup failed for {query!r}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Spotify returned an unexpected search response for {query!r}.")
    tracks = payload.get("tracks")
    items = tracks.get("items") if isinstance(tracks, dict) else None
    if not isinstance(items, list):
        return []
    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        album = item.get("album") if isinstance(item.get("album"), dict) else {}
        artists = item.get("artists") if isinstance(item.get("artists"), list) else []
        artist_names = [str(a.get("name") or "") if isinstance(a, dict) else "" for a in artists]
        artist_ids = [str(a.get("id") or "") if isinstance(a, dict) else "" for a in artists]
        track_id = item.get("id")
        if not isinstance(track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", track_id):
            continue
        records.append({
            "name": item.get("name"),
            "artists": artist_names,
            "artist_ids": artist_ids,
            "artist": artist_names[0] if artist_names else None,
            "artist_id": artist_ids[0] if artist_ids else None,
            "album_id": album.get("id"),
            "album_name": album.get("name"),
            "track_number": item.get("track_number"),
            "disc_number": item.get("disc_number"),
            "duration": item.get("duration_ms"),
            "song_id": track_id,
            "url": (item.get("external_urls") or {}).get("spotify"),
            "search_query": query,
        })
    return records


def _save_spotify_metadata(query: str, output_path: Path | None = None) -> list[dict[str, Any]]:
    """Load full album metadata or return every matching track from Spotify search."""
    Song, Album = _spotify_metadata_library()
    try:
        if query.startswith(SPOTIFY_ALBUM_BASE):
            album = Album.from_url(query, fetch_songs=False)
            records = [track.json for track in album.songs]
        else:
            records = _spotify_search_records(query)
    except Exception as exc:
        raise RuntimeError(f"Spotify metadata lookup failed for {query!r}: {exc}") from exc
    if not all(isinstance(item, dict) for item in records):
        raise RuntimeError(f"Spotify returned unusable metadata records for {query!r}.")
    return records


def _artist_names(record: dict[str, Any]) -> list[str]:
    artists = record.get("artists")
    if isinstance(artists, list):
        return [str(item) for item in artists if isinstance(item, (str, int, float))]
    artist = record.get("artist")
    return [str(artist)] if isinstance(artist, str) else []


SPOTIFY_ARTIST_ALIASES = {
    "tkkg",
    "tkkg retro archiv",
}
SPOTIFY_ARTIST_ID_ALIASES = {"tkkg": "61qDotnjM0jnY5lkfOP7ve"}


def _spotify_artist_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _spotify_artist_matches(record: dict[str, Any]) -> bool:
    aliases = {_spotify_artist_key(value) for value in SPOTIFY_ARTIST_ALIASES}
    return any(_spotify_artist_key(name) in aliases for name in _artist_names(record) if name.strip())


def _spotify_artist_ids(record: dict[str, Any]) -> set[str]:
    aliases = {_spotify_artist_key(value) for value in SPOTIFY_ARTIST_ALIASES}
    artists = _artist_names(record)
    ids = record.get("artist_ids")
    if not isinstance(ids, list):
        return set()
    matched_names = {
        _spotify_artist_key(artist_name)
        for artist_name in artists
        if _spotify_artist_key(artist_name) in aliases
    }
    result = {
        artist_id
        for artist_name, artist_id in zip(artists, ids)
        if _spotify_artist_key(artist_name) in aliases
        and isinstance(artist_id, str)
        and re.fullmatch(r"[A-Za-z0-9]{22}", artist_id)
    }
    for artist_name in matched_names:
        known_id = SPOTIFY_ARTIST_ID_ALIASES.get(artist_name)
        if known_id:
            result.add(known_id)
    return result


def _spotify_number_matches_text(value: str, number: int) -> bool:
    number_pattern = rf"(?<!\d)0*{number}(?!\d)"
    if re.search(number_pattern, value):
        return True
    for match in re.finditer(r"(?<!\d)(\d+)\s*[-–]\s*(\d+)(?!\d)", value):
        if int(match.group(1)) <= number <= int(match.group(2)):
            return True
    return False


def _spotify_album_search_records(
    queries: list[str], episode: dict[str, Any],
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Search Spotify's public album catalogue, including compilation releases."""
    from spotapi import Song as SpotAPISong

    number = int(episode["number"])
    title = _normalise(str(episode["title"]))
    client = SpotAPISong()
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        offset = 0
        for page_index in range(3):
            try:
                payload = client.query_songs(query, limit=100, offset=offset)
            except Exception as exc:
                if diagnostics is not None:
                    diagnostics.append({"album_search_query": query, "offset": offset, "error": str(exc)})
                break
            search = payload.get("data", {}).get("searchV2", {}) if isinstance(payload, dict) else {}
            album_section = search.get("albumsV2", {}) if isinstance(search, dict) else {}
            items = album_section.get("items", []) if isinstance(album_section, dict) else []
            if diagnostics is not None:
                diagnostics.append({
                    "album_search_query": query,
                    "album_search_offset": offset,
                    "album_search_count": len(items) if isinstance(items, list) else 0,
                    "album_search_sample": [
                        (
                            (item.get("data") or item.get("item", {}).get("data") or {}).get("name")
                            if isinstance(item, dict) else None
                        )
                        for item in items[:10]
                    ] if isinstance(items, list) else [],
                })
            if not isinstance(items, list) or not items:
                break
            for wrapper in items:
                if not isinstance(wrapper, dict):
                    continue
                album_data = wrapper.get("data")
                if not isinstance(album_data, dict):
                    nested_item = wrapper.get("item")
                    album_data = nested_item.get("data") if isinstance(nested_item, dict) else None
                if not isinstance(album_data, dict):
                    continue
                album_name = str(album_data.get("name") or "")
                normalized_name = _normalise(album_name)
                album_uri = str(album_data.get("uri") or "")
                album_id = album_uri.rsplit(":", 1)[-1] if album_uri.startswith("spotify:album:") else ""
                if (
                    not album_id
                    or not re.fullmatch(r"[A-Za-z0-9]{22}", album_id)
                    or album_id in seen
                ):
                    continue
                seen.add(album_id)
                album_matches = (
                    title in normalized_name
                    or _spotify_number_matches_text(album_name, number)
                )
                if diagnostics is not None and album_matches:
                    diagnostics.append({"album_search_candidate": album_name, "album_id": album_id})
                if not album_matches:
                    continue
                try:
                    album_records = _save_spotify_metadata(f"{SPOTIFY_ALBUM_BASE}{album_id}")
                except Exception as exc:
                    if diagnostics is not None:
                        diagnostics.append({"album_search_metadata_error": album_name, "error": str(exc)})
                    continue
                for record in album_records:
                    if not _spotify_artist_matches(record):
                        continue
                    record["search_query"] = f"album_search:{query}"
                    records.append(record)
            total = album_section.get("totalCount") if isinstance(album_section, dict) else None
            offset += len(items)
            if len(items) < 100 or (isinstance(total, int) and offset >= total):
                break
    return records


def _spotify_artist_album_records(
    artist_ids: set[str], episode: dict[str, Any],
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Find episode or box albums through the exact credited artist's paginated discography."""
    if not artist_ids:
        if diagnostics is not None:
            diagnostics.append({"discography": "no exact artist IDs were found"})
        return []
    _spotify_metadata_library()
    from spotapi import Artist as SpotAPIArtist

    client = SpotAPIArtist()
    number = int(episode["number"])
    title = _normalise(str(episode["title"]))
    records: list[dict[str, Any]] = []
    seen_albums: set[str] = set()
    for artist_id in sorted(artist_ids):
        if diagnostics is not None:
            diagnostics.append({"discography_artist_id": artist_id})
        if hasattr(client, "paginate_artist_discography"):
            pages = client.paginate_artist_discography(artist_id, section="all")
        elif hasattr(client, "get_artist_discography"):
            def page_generator():
                offset = 0
                while offset < 500:
                    response = client.get_artist_discography(
                        artist_id, section="all", offset=offset, limit=50,
                    )
                    section = (
                        response.get("data", {})
                        .get("artistUnion", {})
                        .get("discography", {})
                        .get("all", {})
                    )
                    page_items = section.get("items") or []
                    if not page_items:
                        break
                    yield page_items
                    offset += len(page_items)
                    total = section.get("totalCount")
                    if len(page_items) < 50 or (isinstance(total, int) and offset >= total):
                        break
            pages = page_generator()
        else:
            raise RuntimeError("Installed SpotAPI does not expose paginated artist discography")
        for page_items in pages:
            if not isinstance(page_items, list):
                continue
            if diagnostics is not None:
                diagnostics.append({
                    "discography_artist_id": artist_id,
                    "discography_count": len(page_items),
                    "discography_sample": [
                        (entry.get("releases", {}).get("items", [{}])[0].get("name"))
                        for entry in page_items[:8]
                        if isinstance(entry, dict)
                        and isinstance(entry.get("releases"), dict)
                        and isinstance(entry["releases"].get("items"), list)
                        and entry["releases"].get("items")
                    ],
                })
            for entry in page_items:
                if not isinstance(entry, dict):
                    continue
                releases = entry.get("releases", {}).get("items", [])
                if not isinstance(releases, list) or not releases or not isinstance(releases[0], dict):
                    continue
                album_item = releases[0]
                album_name = str(album_item.get("name") or "")
                album_id = album_item.get("id")
                if not isinstance(album_id, str):
                    uri = str(album_item.get("uri") or "")
                    album_id = uri.rsplit(":", 1)[-1] if uri.startswith("spotify:album:") else None
                if (
                    not isinstance(album_id, str)
                    or not re.fullmatch(r"[A-Za-z0-9]{22}", album_id)
                    or album_id in seen_albums
                ):
                    continue
                seen_albums.add(album_id)
                album_matches = (
                    title in _normalise(album_name)
                    or _spotify_number_matches_text(album_name, number)
                )
                if diagnostics is not None and album_matches:
                    diagnostics.append({"discography_candidate_album": album_name, "album_id": album_id})
                if not album_matches:
                    continue
                try:
                    album_records = _save_spotify_metadata(f"{SPOTIFY_ALBUM_BASE}{album_id}")
                except Exception as exc:
                    if diagnostics is not None:
                        diagnostics.append({"discography_album_error": album_name, "error": str(exc)})
                    continue
                for record in album_records:
                    record["search_query"] = f"artist_albums:{artist_id} episode:{number}"
                    records.append(record)
    return records


def _episode_title_matches_track(
    episode: dict[str, Any], track: dict[str, Any], candidate_track_id: str | None = None,
) -> bool:
    number = int(episode["number"])
    expected_title = _normalise(str(episode["title"]))
    actual_title = _normalise(str(track.get("name") or ""))
    album_title = _normalise(str(track.get("album_name") or ""))
    part_marker = bool(re.search(r"\bteil\s*0*\d+\b|\bpart\s*0*\d+\b", actual_title))
    title_in_track = bool(expected_title and expected_title in actual_title)
    title_in_album = bool(expected_title and expected_title in album_title)
    if not title_in_track and not (title_in_album and part_marker):
        return False
    return bool(
        _spotify_number_matches_text(actual_title, number)
        or _spotify_number_matches_text(album_title, number)
        or (candidate_track_id and track.get("song_id") == candidate_track_id)
    )


def _spotify_candidate_score(episode: dict[str, Any], record: dict[str, Any]) -> int:
    if not _spotify_artist_matches(record):
        return -100
    name = _normalise(str(record.get("name") or ""))
    title = _normalise(str(episode["title"]))
    number = int(episode["number"])
    album_name = _normalise(str(record.get("album_name") or ""))
    query = _normalise(str(record.get("search_query") or ""))
    number_evidence = (
        _spotify_number_matches_text(name, number)
        or _spotify_number_matches_text(album_name, number)
        or _spotify_number_matches_text(query, number)
    )
    part_marker = bool(re.search(r"\bteil\s*0*\d+\b|\bpart\s*0*\d+\b", name))
    title_in_track = title in name
    title_in_album = title in album_name
    exact_title = name == title
    if not title_in_track and not (title_in_album and part_marker):
        return -100
    if not number_evidence and not exact_title:
        return -100
    score = 100
    if exact_title:
        score += 15
    if part_marker:
        score += 20
    if title_in_album:
        score += 10
    if record.get("track_number") == 1:
        score += 2
    if _spotify_number_matches_text(name, number):
        score += 5
    elif _spotify_number_matches_text(album_name, number):
        score += 3
    return score


def resolve_spotify_album(episode: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Resolve either a dedicated split-track release or the episode track in a compilation."""
    number = int(episode["number"])
    title = str(episode["title"])
    queries = [
        f'track:"{title}" artist:TKKG',
        f'artist:TKKG track:"{title}"',
        f'album:"{title}" artist:TKKG',
        f'artist:TKKG album:"{title}"',
        f'track:"{title}" artist:"TKKG Retro-Archiv"',
        f'track:"{title}"',
        f'track:"TKKG ({number}) - {title}" artist:TKKG',
        f"TKKG ({number}) - {title}",
        f"TKKG {number:03d} {title} Teil 01",
        f"TKKG {number} {title}",
        f"TKKG Folge {number} {title}",
        f"{number} {title}",
        f"{title} TKKG",
        "TKKG",
        "TKKG Retro-Archiv",
    ]
    candidates: dict[str, dict[str, Any]] = {}
    search_errors: list[str] = []
    search_diagnostics: list[dict[str, Any]] = []
    for query in dict.fromkeys(queries):
        try:
            query_records = _save_spotify_metadata(query)[:20]
            if not query_records:
                search_diagnostics.append({"query": query, "result_count": 0})
            for record in query_records[:5]:
                search_diagnostics.append({
                    "query": query,
                    "name": record.get("name"),
                    "artists": _artist_names(record),
                    "artist_ids": record.get("artist_ids"),
                    "album_name": record.get("album_name"),
                    "score": _spotify_candidate_score(episode, record),
                })
                track_id = record.get("song_id")
                if isinstance(track_id, str):
                    existing = candidates.get(track_id)
                    if existing is None or _spotify_candidate_score(episode, record) > _spotify_candidate_score(episode, existing):
                        candidates[track_id] = record
        except Exception as exc:
            search_errors.append(f"{query}: {exc}")

    ranked = sorted(
        (( _spotify_candidate_score(episode, record), track_id, record)
         for track_id, record in candidates.items()),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    ranked = [item for item in ranked if item[0] >= 100]
    if not ranked:
        box_start = ((number - 1) // 3) * 3 + 1
        box_end = box_start + 2
        box_index = ((number - 1) // 3) + 1
        box_title = f"{box_index:02d}/3er Box - Folge {box_start}-{box_end}"
        album_queries = list(dict.fromkeys([
            title,
            f"TKKG {number} {title}",
            box_title,
            f"TKKG {box_title}",
            f"TKKG {box_start}-{box_end}",
            f"3er Box Folge {box_start}-{box_end}",
            f"Folge {box_start}-{box_end} TKKG",
        ]))
        try:
            for record in _spotify_album_search_records(album_queries, episode, search_diagnostics):
                track_id = record.get("song_id")
                if isinstance(track_id, str):
                    candidates[track_id] = record
        except Exception as exc:
            search_errors.append(f"Spotify album search: {exc}")
        ranked = sorted(
            ((_spotify_candidate_score(episode, record), track_id, record)
             for track_id, record in candidates.items()),
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        ranked = [item for item in ranked if item[0] >= 100]
    if not ranked:
        artist_ids = {
            artist_id
            for record in candidates.values()
            for artist_id in _spotify_artist_ids(record)
        }
        try:
            for record in _spotify_artist_album_records(artist_ids, episode, search_diagnostics):
                track_id = record.get("song_id")
                if isinstance(track_id, str):
                    existing = candidates.get(track_id)
                    if existing is None or _spotify_candidate_score(episode, record) > _spotify_candidate_score(episode, existing):
                        candidates[track_id] = record
        except Exception as exc:
            search_errors.append(f"artist discography: {exc}")
        ranked = sorted(
            ((_spotify_candidate_score(episode, record), track_id, record)
             for track_id, record in candidates.items()),
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        ranked = [item for item in ranked if item[0] >= 100]
    if not ranked:
        detail = "; ".join(search_errors[:3]) or "no title and artist candidate passed validation"
        diagnostics = json.dumps(search_diagnostics[:100], ensure_ascii=False)
        raise ValueError(f"No credible Spotify track candidate for episode {number}: {detail}. Candidates: {diagnostics}")

    album_cache: dict[str, list[dict[str, Any]]] = {}
    verified: list[tuple[int, str, str, list[dict[str, Any]], str]] = []
    rejected: list[str] = []
    for score, track_id, candidate in ranked[:12]:
        album_id = candidate.get("album_id")
        album_name = candidate.get("album_name")
        if not isinstance(album_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", album_id):
            rejected.append(f"{track_id}: missing valid album ID")
            continue
        if not isinstance(album_name, str) or not album_name.strip():
            rejected.append(f"{track_id}: missing album title")
            continue
        if album_id not in album_cache:
            try:
                album_cache[album_id] = _save_spotify_metadata(f"{SPOTIFY_ALBUM_BASE}{album_id}")
            except Exception as exc:
                rejected.append(f"{album_id}: album metadata failed: {exc}")
                continue
        album_tracks = album_cache[album_id]
        if not album_tracks or any(item.get("album_id") != album_id for item in album_tracks):
            rejected.append(f"{album_id}: inconsistent album metadata")
            continue
        selected = [item for item in album_tracks if _episode_title_matches_track(episode, item, track_id)]
        if not selected:
            # A track-level search hit can be trusted only if its identity also appears
            # in the fetched parent album tracklist.
            selected = [item for item in album_tracks if item.get("song_id") == track_id]
            if not selected or not _episode_title_matches_track(episode, selected[0], track_id):
                rejected.append(f"{album_id}: requested episode could not be isolated from album")
                continue
        selected.sort(key=lambda item: (
            int(item.get("disc_number") or 1),
            int(item.get("track_number") or 0),
        ))
        numbers = [int(item.get("track_number") or 0) for item in selected]
        if any(value < 1 for value in numbers) or len(set((item.get("disc_number") or 1, item.get("track_number")) for item in selected)) != len(selected):
            rejected.append(f"{album_id}: selected episode tracks have invalid or duplicate positions")
            continue
        if len(selected) > 1 and numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            rejected.append(f"{album_id}: selected episode tracks are not contiguous")
            continue
        if not all(isinstance(item.get("name"), str) and item["name"].strip() for item in selected):
            rejected.append(f"{album_id}: selected track has no title")
            continue
        verified.append((score, album_id, album_name, selected, track_id))

    if not verified:
        detail = "; ".join(rejected[:8]) or "no candidate album could be validated"
        raise ValueError(f"Spotify candidates for episode {number} were rejected: {detail}")
    verified.sort(key=lambda item: (item[0], len(item[3])), reverse=True)
    best = verified[0]
    if len(verified) > 1 and verified[1][0] == best[0] and verified[1][1] != best[1]:
        raise ValueError(
            f"Ambiguous Spotify match for episode {number}: "
            f"{best[1]} and {verified[1][1]} have equal evidence scores."
        )
    _, album_id, album_name, records, selected_track_id = best
    album_url = f"{SPOTIFY_ALBUM_BASE}{album_id}"
    return {
        "album_id": album_id,
        "url": album_url,
        "title": album_name,
        "track_count": len(records),
        "tracks": records,
        "source_query": next(
            (str(item.get("search_query")) for item in candidates.values()
             if item.get("song_id") == selected_track_id),
            queries[0],
        ),
        "release_type": (
            "compilation_track_selection"
            if len(records) < len(album_cache[album_id])
            else "episode_release"
        ),
        "selected_track_id": selected_track_id,
    }


def _candidate_source(candidate: dict[str, Any], filter_name: str) -> tuple[str, str] | None:
    playlist_id = candidate.get("playlistId") or candidate.get("audioPlaylistId")
    if isinstance(playlist_id, str) and playlist_id.startswith(("OLAK5uy_", "PL")):
        return "playlist", playlist_id
    browse_id = candidate.get("browseId")
    if isinstance(browse_id, str) and browse_id.startswith(("VLPL", "VLOLAK5uy_")):
        return "playlist", browse_id[2:]
    if filter_name == "albums" and isinstance(browse_id, str) and browse_id.startswith("MPRE"):
        return "album", browse_id
    return None


def _candidate_artists(candidate: dict[str, Any], playlist: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for source in (candidate, playlist):
        for key in ("artist", "author"):
            value = source.get(key)
            if isinstance(value, str):
                values.append(value)
        for key in ("artists", "artist"):
            value = source.get(key)
            if isinstance(value, list):
                values.extend(
                    str(item.get("name", "")) if isinstance(item, dict) else str(item)
                    for item in value
                )
    for track in playlist.get("tracks", []):
        if not isinstance(track, dict):
            continue
        artists = track.get("artists")
        if isinstance(artists, list):
            values.extend(
                str(item.get("name", "")) if isinstance(item, dict) else str(item)
                for item in artists
            )
    return [value for value in values if value.strip()]


def _track_titles_match(spotify_tracks: list[dict[str, Any]], ytm_tracks: list[dict[str, Any]]) -> bool:
    if not spotify_tracks or len(spotify_tracks) != len(ytm_tracks):
        return False
    for spotify_track, ytm_track in zip(spotify_tracks, ytm_tracks, strict=True):
        spotify_title = spotify_track.get("name")
        ytm_title = ytm_track.get("title")
        if not isinstance(spotify_title, str) or not isinstance(ytm_title, str):
            return False
        if _normalise(spotify_title) != _normalise(ytm_title):
            return False
    return True


def find_verified_youtube_music_playlist(
    episode: dict[str, Any], spotify: dict[str, Any], ytm: Any,
    playlist_id_override: str | None = None,
) -> dict[str, Any]:
    number = int(episode["number"])
    title = str(episode["title"])
    if playlist_id_override:
        if not playlist_id_override.startswith(("OLAK5uy_", "PL")):
            raise ValueError("The supplied YouTube Music playlist ID has an unsupported format.")
        playlist_url = f"{YTM_BASE}{urlencode({'list': playlist_id_override})}"
        info = _extract_ytdlp_playlist(playlist_url)
        returned_id = info.get("id")
        if returned_id is not None and returned_id != playlist_id_override:
            raise ValueError(
                f"yt-dlp returned playlist ID {returned_id!r}, expected {playlist_id_override!r}."
            )
        playlist_title = str(info.get("title") or "")
        if _normalise(title) not in _normalise(playlist_title):
            raise ValueError(
                f"YouTube Music playlist title {playlist_title!r} does not identify episode {number}."
            )
        entries = info.get("entries")
        if not isinstance(entries, list) or not entries or any(entry is None for entry in entries):
            raise ValueError("yt-dlp did not return a complete YouTube Music playlist track list.")
        playlist_count = info.get("playlist_count") or len(entries)
        if playlist_count != spotify["track_count"] or len(entries) != spotify["track_count"]:
            raise ValueError(
                f"YouTube Music playlist has {len(entries)} entries, "
                f"expected {spotify['track_count']} Spotify tracks."
            )
        matched_tracks = _playlist_track_records(
            spotify, entries, playlist_title, explicit_playlist_id=True,
        )
        return {
            "playlist_id": playlist_id_override,
            "url": playlist_url,
            "title": playlist_title,
            "track_count": len(entries),
            "_matched_tracks": matched_tracks,
        }

    query_variants = [
        f"TKKG {number:03d} {title}",
        f"TKKG Folge {number} {title}",
        f"{number} {title}",
        f"TKKG {spotify['title']}",
        str(spotify["title"]),
    ]
    query_variants.extend(
        f"TKKG {track['name']}" for track in spotify["tracks"][:3]
        if isinstance(track.get("name"), str)
    )
    queries = tuple(dict.fromkeys(query.strip() for query in query_variants if query.strip()))
    candidates: dict[str, tuple[str, str, dict[str, Any]]] = {}
    search_summaries: list[dict[str, Any]] = []
    for query in queries:
        for filter_name in ("albums", "playlists"):
            try:
                time.sleep(0.35)
                results = ytm.search(query, filter=filter_name, limit=10)
            except Exception as exc:
                raise RuntimeError(f"YouTube Music search failed for {query!r}: {exc}") from exc
            for result in results:
                if not isinstance(result, dict):
                    continue
                search_summaries.append({key: result.get(key) for key in ("resultType", "title", "browseId", "playlistId", "audioPlaylistId", "artist", "artists") if result.get(key) is not None} | {"filter": filter_name, "query": query})
                candidate_title = str(result.get("title") or "")
                if _normalise(title) not in _normalise(candidate_title):
                    continue
                source = _candidate_source(result, filter_name)
                if source is None:
                    continue
                kind, source_id = source
                key = f"{kind}:{source_id}"
                if key not in candidates and len(candidates) < 8:
                    candidates[key] = (kind, source_id, result)

    verified: dict[str, dict[str, Any]] = {}
    rejected: list[str] = []
    for kind, source_id, candidate in candidates.values():
        try:
            time.sleep(0.35)
            if kind == "album":
                album = ytm.get_album(source_id)
                if not isinstance(album, dict):
                    rejected.append(f"{source_id}: malformed album response")
                    continue
                candidate = {**candidate, **album}
                playlist_id = album.get("audioPlaylistId")
                if not isinstance(playlist_id, str) or not playlist_id.startswith("OLAK5uy_"):
                    album_title = str(album.get("title") or candidate.get("title") or "")
                    album_tracks = album.get("tracks")
                    artist_names = _candidate_artists(candidate, {})
                    if not any(
                        re.search(r"\btkkg\b", unicodedata.normalize("NFKC", name).casefold())
                        for name in artist_names
                    ):
                        rejected.append(f"{source_id}: no TKKG artist evidence")
                        continue
                    if _normalise(title) not in _normalise(album_title):
                        rejected.append(f"{source_id}: album title does not identify episode {number}")
                        continue
                    if not isinstance(album_tracks, list) or len(album_tracks) != spotify["track_count"]:
                        rejected.append(
                            f"{source_id}: no public playlist ID and album track list is incomplete "
                            f"({len(album_tracks) if isinstance(album_tracks, list) else 0} entries)"
                        )
                        continue
                    album_url = f"https://music.youtube.com/browse/{source_id}"
                    try:
                        matched_tracks = _playlist_track_records(
                            spotify, album_tracks, album_title,
                            explicit_playlist_id=False, source_type="album",
                        )
                    except ValueError as metadata_error:
                        try:
                            album_info = _extract_ytdlp_playlist(album_url)
                            extracted_entries = album_info.get("entries")
                            if (
                                not isinstance(extracted_entries, list)
                                or len(extracted_entries) != spotify["track_count"]
                                or any(entry is None for entry in extracted_entries)
                            ):
                                raise ValueError(
                                    "yt-dlp did not extract the complete album tracklist"
                                )
                            matched_tracks = _playlist_track_records(
                                spotify, extracted_entries,
                                str(album_info.get("title") or album_title),
                                explicit_playlist_id=False, source_type="album",
                            )
                        except Exception as extraction_error:
                            track_preview = [
                                {
                                    key: track.get(key)
                                    for key in (
                                        "title", "videoId", "video_id", "id", "duration",
                                        "duration_seconds", "artists", "album",
                                    )
                                    if track.get(key) is not None
                                }
                                for track in album_tracks[:3]
                                if isinstance(track, dict)
                            ]
                            rejected.append(
                                f"{source_id}: album metadata could not provide verified video IDs "
                                f"({metadata_error}); yt-dlp album page extraction failed "
                                f"({extraction_error}); track preview: "
                                f"{json.dumps(track_preview, ensure_ascii=False)}"
                            )
                            continue
                    verified[f"album:{source_id}"] = {
                        "playlist_id": None,
                        "url": None,
                        "album_id": source_id,
                        "album_url": album_url,
                        "title": album_title,
                        "track_count": len(album_tracks),
                        "_matched_tracks": matched_tracks,
                    }
                    continue
            else:
                playlist_id = source_id
            if playlist_id in verified:
                continue
            playlist_url = f"{YTM_BASE}{urlencode({'list': playlist_id})}"
            info = _extract_ytdlp_playlist(playlist_url)
        except Exception as exc:
            rejected.append(f"{source_id}: playlist or album retrieval failed: {exc}")
            continue
        playlist_title = str(info.get("title") or candidate.get("title") or "")
        if _normalise(title) not in _normalise(playlist_title):
            rejected.append(f"{playlist_id}: title does not identify episode {number}")
            continue
        entries = info.get("entries")
        if not isinstance(entries, list) or not entries or any(entry is None for entry in entries):
            rejected.append(f"{playlist_id}: no complete track list returned")
            continue
        if info.get("playlist_count", len(entries)) != spotify["track_count"] or len(entries) != spotify["track_count"]:
            rejected.append(f"{playlist_id}: playlist track count does not match Spotify")
            continue
        artist_names = _candidate_artists(candidate, {})
        if not any(re.search(r"\btkkg\b", unicodedata.normalize("NFKC", name).casefold()) for name in artist_names):
            rejected.append(f"{playlist_id}: no TKKG artist evidence")
            continue
        try:
            matched_tracks = _playlist_track_records(
                spotify, entries, playlist_title, explicit_playlist_id=False,
            )
        except ValueError as exc:
            rejected.append(f"{playlist_id}: {exc}")
            continue
        verified[playlist_id] = {
            "playlist_id": playlist_id,
            "url": playlist_url,
            "title": playlist_title,
            "track_count": len(entries),
            "_matched_tracks": matched_tracks,
        }

    if len(verified) == 0:
        detail = "; ".join(rejected[:12]) or "no matching album or playlist candidates found"
        search_detail = json.dumps(search_summaries[:30], ensure_ascii=False)
        raise ValueError(
            f"No verified YouTube Music playlist for episode {number}: {detail}. "
            f"Search results: {search_detail}"
        )
    if len(verified) > 1:
        ids = ", ".join(sorted(verified))
        raise ValueError(f"Ambiguous YouTube Music match for episode {number}; verified candidates: {ids}")
    return next(iter(verified.values()))



def _ytm_artist_names(track: dict[str, Any]) -> list[str]:
    artists = track.get("artists") or []
    if isinstance(artists, str):
        return [artists]
    return [
        str(item.get("name", "")) if isinstance(item, dict) else str(item)
        for item in artists
    ]


def _duration_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        # spotDL's duration field is seconds; the raw Spotify API duration_ms field is milliseconds.
        return float(value) if value < 10000 else float(value) / 1000
    if isinstance(value, str):
        parts = value.strip().split(":")
        try:
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60 + float(part)
            return seconds
        except ValueError:
            return None
    return None


def _spotify_track_identity(spotify_track: dict[str, Any], index: int) -> tuple[str, str]:
    spotify_track_id = spotify_track.get("song_id")
    spotify_track_url = spotify_track.get("url")
    if not isinstance(spotify_track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_track_id):
        if isinstance(spotify_track_url, str):
            match = re.fullmatch(r"https://open\.spotify\.com/track/([A-Za-z0-9]{22})", spotify_track_url)
            spotify_track_id = match.group(1) if match else None
    if not isinstance(spotify_track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_track_id):
        raise ValueError(f"Spotify track {index} has no valid track ID.")
    expected_url = f"https://open.spotify.com/track/{spotify_track_id}"
    if spotify_track_url is not None and spotify_track_url != expected_url:
        raise ValueError(f"Spotify track {index} URL does not match its track ID.")
    return spotify_track_id, expected_url


def _extract_ytdlp_playlist(playlist_url: str) -> dict[str, Any]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError("yt-dlp is required to inspect YouTube Music playlist entries.") from exc
    options = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    if not isinstance(info, dict):
        raise ValueError("yt-dlp returned an invalid YouTube Music playlist response.")
    return info


def _playlist_track_records(
    spotify: dict[str, Any],
    playlist_tracks: list[dict[str, Any]],
    playlist_title: str,
    *,
    explicit_playlist_id: bool,
    source_type: str = "playlist",
) -> list[dict[str, Any]]:
    if len(playlist_tracks) != spotify["track_count"]:
        raise ValueError(
            f"YouTube Music playlist has {len(playlist_tracks)} entries, "
            f"expected {spotify['track_count']} Spotify tracks."
        )
    resolved: list[dict[str, Any]] = []
    for index, (spotify_track, candidate) in enumerate(
        zip(spotify["tracks"], playlist_tracks, strict=True), start=1,
    ):
        if not isinstance(candidate, dict):
            raise ValueError(f"YouTube Music playlist entry {index} is malformed.")
        spotify_title = str(spotify_track.get("name") or "")
        ytm_title = str(candidate.get("title") or "")
        if not ytm_title or _normalise(spotify_title) != _normalise(ytm_title):
            raise ValueError(
                f"YouTube Music playlist entry {index} does not match Spotify track "
                f"{spotify_title!r}: {ytm_title!r}."
            )
        video_id = candidate.get("id") or candidate.get("videoId")
        if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raw_url = candidate.get("url")
            if isinstance(raw_url, str):
                video_id = parse_qs(urlparse(raw_url).query).get("v", [None])[0]
        if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError(f"YouTube Music playlist entry {index} has no valid video ID.")

        spotify_track_id, spotify_track_url = _spotify_track_identity(spotify_track, index)
        ytm_duration = _duration_seconds(candidate.get("duration_seconds") or candidate.get("duration"))
        spotify_duration = _duration_seconds(spotify_track.get("duration") or spotify_track.get("duration_ms"))
        evidence = [
            "exact_normalised_title",
            f"ordered_{source_type}_match",
            f"{source_type}_title_matches_episode",
        ]
        if explicit_playlist_id:
            evidence.append("explicit_playlist_id")
        if ytm_duration is not None and spotify_duration is not None:
            difference = abs(ytm_duration - spotify_duration)
            if difference > 8:
                raise ValueError(
                    f"YouTube Music playlist entry {index} duration differs from Spotify "
                    f"by {difference:.1f} seconds."
                )
            evidence.append("duration_within_8_seconds")

        album = candidate.get("album")
        album_name = album.get("name") if isinstance(album, dict) else album
        resolved.append({
            "track_number": index,
            "spotify_title": spotify_title,
            "spotify_track_id": spotify_track_id,
            "spotify_track_url": spotify_track_url,
            "video_id": video_id,
            "url": f"https://music.youtube.com/watch?v={video_id}",
            "title": ytm_title,
            "artists": _ytm_artist_names(candidate),
            "album": str(album_name or playlist_title),
            "duration_seconds": round(ytm_duration, 2) if ytm_duration is not None else None,
            "match_score": 160 if ytm_duration is not None else 140,
            "match_evidence": evidence,
        })
    return resolved



def _ytm_track_score(
    spotify_track: dict[str, Any], candidate: dict[str, Any], spotify_album_title: str,
    episode_title: str,
) -> tuple[int, list[str]]:
    expected_title = str(spotify_track.get("name") or "")
    candidate_title = str(candidate.get("title") or "")
    if not expected_title or _normalise(expected_title) != _normalise(candidate_title):
        return 0, []
    score = 100
    evidence = ["exact_normalised_title"]
    artists = _ytm_artist_names(candidate)
    if any(re.search(r"\btkkg\b", name.casefold()) for name in artists):
        score += 30
        evidence.append("tkkg_artist")
    album = candidate.get("album")
    album_name = str(album.get("name", "")) if isinstance(album, dict) else str(album or "")
    if album_name and (
        _normalise(album_name) == _normalise(spotify_album_title)
        or _normalise(episode_title) in _normalise(album_name)
    ):
        score += 40
        evidence.append("episode_album")
    spotify_duration = _duration_seconds(spotify_track.get("duration"))
    ytm_duration = _duration_seconds(candidate.get("duration_seconds") or candidate.get("duration"))
    if spotify_duration is not None and ytm_duration is not None:
        delta = abs(spotify_duration - ytm_duration)
        if delta <= 3:
            score += 20
            evidence.append("duration_within_3_seconds")
        elif delta <= 8:
            score += 10
            evidence.append("duration_within_8_seconds")
    return score, evidence


def find_verified_youtube_music_tracks(
    episode: dict[str, Any], spotify: dict[str, Any], ytm: Any,
) -> list[dict[str, Any]]:
    """Resolve every Spotify track to one unambiguous YouTube Music song."""
    resolved: list[dict[str, Any]] = []
    for index, spotify_track in enumerate(spotify["tracks"], start=1):
        title = str(spotify_track["name"])
        query_variants = (
            title,
            f"TKKG {title}",
            f"TKKG Folge {int(episode['number'])} {episode['title']} Teil {index:02d}",
        )
        ranked: dict[str, tuple[int, dict[str, Any], list[str]]] = {}
        candidate_diagnostics: list[dict[str, Any]] = []
        search_errors: list[str] = []
        for query in dict.fromkeys(query_variants):
            try:
                time.sleep(0.35)
                results = ytm.search(query, filter="songs", limit=10)
            except Exception as exc:
                search_errors.append(f"{query!r}: {exc}")
                continue
            for candidate in results:
                if not isinstance(candidate, dict):
                    continue
                video_id = candidate.get("videoId")
                score, evidence = _ytm_track_score(
                    spotify_track, candidate, str(spotify["title"]), str(episode["title"]),
                )
                artists = _ytm_artist_names(candidate)
                album = candidate.get("album")
                album_name = album.get("name") if isinstance(album, dict) else album
                diagnostic = {
                    "query": query,
                    "title": candidate.get("title"),
                    "artists": artists[:5],
                    "album": album_name,
                    "duration": candidate.get("duration_seconds") or candidate.get("duration"),
                    "video_id": video_id,
                    "score": score,
                    "evidence": evidence,
                }
                if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                    diagnostic["rejection_reason"] = "missing or invalid video ID"
                    candidate_diagnostics.append(diagnostic)
                    continue
                if score < 130:
                    diagnostic["rejection_reason"] = "score below unchanged threshold of 130"
                    candidate_diagnostics.append(diagnostic)
                    continue
                previous = ranked.get(video_id)
                if previous is None or score > previous[0]:
                    ranked[video_id] = (score, candidate, evidence)
                candidate_diagnostics.append(diagnostic)
        if not ranked and search_errors and not candidate_diagnostics:
            raise RuntimeError(
                f"YouTube Music song search failed for track {index} {title!r}: "
                + "; ".join(search_errors[:3])
            )

        if not ranked:
            detail = json.dumps(candidate_diagnostics[:10], ensure_ascii=False)
            raise ValueError(
                f"No sufficiently corroborated YouTube Music song match for track {index}: "
                f"{title!r}. Candidate diagnostics: {detail}. "
                f"Search errors: {search_errors[:3]}"
            )
        ordered = sorted(ranked.values(), key=lambda item: item[0], reverse=True)
        if len(ordered) > 1 and ordered[0][0] - ordered[1][0] < 15:
            ids = [item[1].get("videoId") for item in ordered[:4]]
            detail = json.dumps(candidate_diagnostics[:10], ensure_ascii=False)
            raise ValueError(
                f"Ambiguous YouTube Music song match for track {index} {title!r}: "
                f"{ids}. Candidate diagnostics: {detail}"
            )
        score, candidate, evidence = ordered[0]
        video_id = str(candidate["videoId"])
        spotify_track_id = spotify_track.get("song_id")
        spotify_track_url = spotify_track.get("url")
        if not isinstance(spotify_track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_track_id):
            if isinstance(spotify_track_url, str):
                match = re.fullmatch(r"https://open\.spotify\.com/track/([A-Za-z0-9]{22})", spotify_track_url)
                spotify_track_id = match.group(1) if match else None
        if not isinstance(spotify_track_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_track_id):
            raise ValueError(f"Spotify track {index} has no valid track ID.")
        expected_spotify_url = f"https://open.spotify.com/track/{spotify_track_id}"
        if spotify_track_url is not None and spotify_track_url != expected_spotify_url:
            raise ValueError(f"Spotify track {index} URL does not match its track ID.")
        spotify_track_url = expected_spotify_url
        duration = _duration_seconds(candidate.get("duration_seconds") or candidate.get("duration"))
        album = candidate.get("album")
        album_name = album.get("name") if isinstance(album, dict) else album
        resolved.append({
            "track_number": index,
            "spotify_title": title,
            "spotify_track_id": spotify_track_id,
            "spotify_track_url": spotify_track_url,
            "video_id": video_id,
            "url": f"https://music.youtube.com/watch?v={video_id}",
            "title": str(candidate.get("title") or title),
            "artists": _ytm_artist_names(candidate),
            "album": str(album_name) if album_name else None,
            "duration_seconds": round(duration, 2) if duration is not None else None,
            "match_score": score,
            "match_evidence": evidence,
        })
    if len(resolved) != spotify["track_count"]:
        raise ValueError("YouTube Music individual track count does not match Spotify.")
    return resolved


class AudioDiscoveryError(ValueError):
    def __init__(
        self, message: str, *, stage: str, spotify: dict[str, Any] | None = None,
        playlist_error: str | None = None, timings: dict[str, float] | None = None,
    ):
        super().__init__(message)
        self.stage = stage
        self.spotify = spotify
        self.playlist_error = playlist_error
        self.timings = timings or {}


def _spotify_links(spotify: dict[str, Any]) -> dict[str, Any]:
    return {
        "album": spotify["url"],
        "tracks": [
            {
                "track_number": int(track["track_number"]),
                "title": track["name"],
                "url": _spotify_track_identity(track, index)[1],
            }
            for index, track in enumerate(spotify["tracks"], start=1)
        ],
    }


def _release_links(
    spotify: dict[str, Any], playlist: dict[str, Any] | None,
    youtube_music_tracks: list[dict[str, Any]], album_url: str | None = None,
) -> dict[str, Any]:
    return {
        "spotify_album": spotify["url"],
        "spotify_tracks": _spotify_links(spotify)["tracks"],
        "youtube_music_playlist": playlist["url"] if playlist else None,
        "youtube_music_album": album_url,
        "youtube_music_tracks": [
            {
                "track_number": track["track_number"],
                "title": track["title"],
                "url": track["url"],
                "spotify_url": track["spotify_track_url"],
            }
            for track in youtube_music_tracks
        ],
    }


def discover_episode_audio(
    episode: dict[str, Any], ytm: Any, playlist_id_override: str | None = None,
) -> dict[str, Any]:
    total_started = time.perf_counter()
    spotify_started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix=f"tkkg_audio_{episode['number']:03d}_") as temp:
            spotify = resolve_spotify_album(episode, Path(temp))
    except Exception as exc:
        timings = {
            "spotify_seconds": round(time.perf_counter() - spotify_started, 2),
            "total_seconds": round(time.perf_counter() - total_started, 2),
        }
        raise AudioDiscoveryError(
            f"Spotify metadata resolution failed: {exc}", stage="spotify",
            timings=timings,
        ) from exc
    spotify_seconds = round(time.perf_counter() - spotify_started, 2)

    # Search complete playlists first, then use individual song matching only
    # as a fallback. Never lower the existing matching threshold.
    youtube_music_playlist = None
    youtube_music_album = None
    playlist_failure = None
    youtube_music_tracks = None
    playlist_started = time.perf_counter()
    if spotify.get("release_type") == "compilation_track_selection":
        playlist_failure = (
            "Album-level playlist pairing skipped because the Spotify source is a compilation; "
            "only individual episode track pairs are safe."
        )
    else:
        try:
            playlist_result = find_verified_youtube_music_playlist(
                episode, spotify, ytm, playlist_id_override,
            )
            youtube_music_tracks = playlist_result.pop("_matched_tracks")
            if playlist_result.get("playlist_id"):
                youtube_music_playlist = playlist_result
            else:
                youtube_music_album = playlist_result.get("album_url")
        except Exception as exc:
            playlist_failure = str(exc)
    playlist_seconds = round(time.perf_counter() - playlist_started, 2)

    song_search_seconds = 0.0
    if youtube_music_tracks is None:
        song_started = time.perf_counter()
        try:
            youtube_music_tracks = find_verified_youtube_music_tracks(episode, spotify, ytm)
        except Exception as exc:
            song_search_seconds = round(time.perf_counter() - song_started, 2)
            timings = {
                "spotify_seconds": spotify_seconds,
                "playlist_seconds": playlist_seconds,
                "individual_song_search_seconds": song_search_seconds,
                "total_seconds": round(time.perf_counter() - total_started, 2),
            }
            raise AudioDiscoveryError(
                f"YouTube Music track resolution failed: {exc}. "
                f"Complete playlist discovery also failed: {playlist_failure}",
                stage="youtube_music", spotify=spotify, playlist_error=playlist_failure,
                timings=timings,
            ) from exc
        song_search_seconds = round(time.perf_counter() - song_started, 2)

    timings = {
        "spotify_seconds": spotify_seconds,
        "playlist_seconds": playlist_seconds,
        "individual_song_search_seconds": song_search_seconds,
        "total_seconds": round(time.perf_counter() - total_started, 2),
    }
    verified_at = datetime.now(timezone.utc).isoformat()
    audio_release = {
        "spotify": {
            "album_id": spotify["album_id"],
            "url": spotify["url"],
            "title": spotify["title"],
            "track_count": spotify["track_count"],
            "source_query": spotify["source_query"],
        },
        "youtube_music": {
            "playlist": youtube_music_playlist,
            "tracks": youtube_music_tracks,
            "track_count": len(youtube_music_tracks),
        },
        "verification": {
            "status": "verified",
            "verified_at": verified_at,
            "method": (
                "exact_ordered_playlist_track_titles_and_duration"
                if youtube_music_playlist
                else "exact_ordered_album_track_titles_and_duration"
                if youtube_music_album
                else "exact_track_titles_with_artist_album_or_duration_corroboration"
            ),
            "matched_track_count": len(youtube_music_tracks),
            "playlist_status": "verified" if youtube_music_playlist else "unavailable",
            "playlist_error": playlist_failure,
        },
    }
    matched_tracks = [
        {
            "spotify_title": spotify_track["name"],
            "spotify_track_url": ytm_track["spotify_track_url"],
            "youtube_music_title": ytm_track["title"],
            "youtube_music_url": ytm_track["url"],
            "match_evidence": ytm_track["match_evidence"],
        }
        for spotify_track, ytm_track in zip(
            spotify["tracks"], youtube_music_tracks, strict=True,
        )
    ]
    return {
        "audio_release": audio_release,
        "matched_tracks": matched_tracks,
        "links": _release_links(
            spotify, youtube_music_playlist, youtube_music_tracks, youtube_music_album,
        ),
        "timings": timings,
    }



def audio_release_coverage(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    verified = [
        item for item in episodes
        if isinstance(item.get("audio_release"), dict)
        and item["audio_release"].get("verification", {}).get("status") == "verified"
    ]
    return {
        "episode_count": len(episodes),
        "verified_pairings": len(verified),
        "missing_pairings": [
            {"number": item.get("number"), "title": item.get("title")}
            for item in episodes if item not in verified
        ],
    }


def preserve_verified_audio_releases(
    episodes: list[dict[str, Any]], previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    previous_by_number = {
        item.get("number"): item.get("audio_release")
        for item in previous
        if isinstance(item.get("audio_release"), dict)
        and item["audio_release"].get("verification", {}).get("status") == "verified"
    }
    conflicts: list[dict[str, Any]] = []
    for episode in episodes:
        old = previous_by_number.get(episode.get("number"))
        if old is None:
            continue
        current = episode.get("audio_release")
        if current is None:
            episode["audio_release"] = deepcopy(old)
        elif current != old:
            episode["audio_release"] = deepcopy(old)
            conflicts.append({
                "number": episode.get("number"),
                "reason": "new audio metadata differed from the previously verified mapping; previous mapping retained",
            })
    return conflicts


def _load_ytmusic() -> Any:
    try:
        import requests
        from ytmusicapi import YTMusic
    except ImportError as exc:
        raise RuntimeError(
            "ytmusicapi is not installed. Install requirements-audio.txt first."
        ) from exc
    session = requests.Session()
    session.request = partial(session.request, timeout=20)
    return YTMusic(requests_session=session)


def enrich_catalogue(
    episodes: list[dict[str, Any]], *, selected_numbers: set[int] | None = None,
    limit: int = 5, write: bool = False, ytm: Any = None,
    catalogue_path: Path = CATALOGUE_PATH, latest_first: bool = False,
    playlist_id_override: str | None = None,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be at least 1.")
    targets = [
        item for item in episodes
        if (selected_numbers is None or item.get("number") in selected_numbers)
        and (
            selected_numbers is not None
            or not (
                isinstance(item.get("audio_release"), dict)
                and item["audio_release"].get("verification", {}).get("status") == "verified"
            )
        )
    ]
    if latest_first:
        targets.sort(key=lambda item: int(item.get("number", 0)), reverse=True)
    targets = targets[:limit]
    run_started = time.perf_counter()
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "write" if write else "dry_run",
        "target_count": len(targets),
        "selected_numbers": [int(item["number"]) for item in targets],
        "verified": [],
        "failures": [],
        "coverage_before": audio_release_coverage(episodes),
        "catalogue_updated": False,
    }
    if targets and ytm is None:
        ytm = _load_ytmusic()
    for episode in targets:
        number = episode.get("number")
        print(f"Discovering audio sources for episode {number}: {episode.get('title')}", flush=True)
        try:
            discovery = discover_episode_audio(episode, ytm, playlist_id_override)
            audio_release = discovery["audio_release"]
        except Exception as exc:
            failure = {
                "number": number,
                "title": episode.get("title"),
                "stage": getattr(exc, "stage", "unknown"),
                "error": str(exc),
                "timings": getattr(exc, "timings", {}),
            }
            partial_spotify = getattr(exc, "spotify", None)
            if isinstance(partial_spotify, dict):
                failure["spotify"] = {
                    "album_id": partial_spotify["album_id"],
                    "title": partial_spotify["title"],
                    "track_count": partial_spotify["track_count"],
                }
                failure["links"] = {
                    "spotify_album": partial_spotify["url"],
                    "spotify_tracks": _spotify_links(partial_spotify)["tracks"],
                    "youtube_music_playlist": None,
                    "youtube_music_album": None,
                    "youtube_music_tracks": [],
                }
                failure["playlist_error"] = getattr(exc, "playlist_error", None)
            report["failures"].append(failure)
            print(f"  unresolved: {exc}", flush=True)
            continue
        report["verified"].append({
            "number": number,
            "title": episode.get("title"),
            "audio_release": audio_release,
            "matched_tracks": discovery["matched_tracks"],
            "links": discovery["links"],
            "timings": discovery["timings"],
        })
        playlist = audio_release["youtube_music"].get("playlist")
        playlist_note = (
            f", playlist {playlist['playlist_id']}" if isinstance(playlist, dict)
            else ", verified album tracklist" if discovery["links"].get("youtube_music_album")
            else ", no verified album playlist"
        )
        print(
            f"  verified: {audio_release['spotify']['track_count']} Spotify and "
            f"{audio_release['youtube_music']['track_count']} YouTube Music track links"
            f"{playlist_note}",
            flush=True,
        )
        if write:
            existing_release = episode.get("audio_release")
            if (
                isinstance(existing_release, dict)
                and existing_release.get("verification", {}).get("status") == "verified"
                and existing_release != audio_release
            ):
                report.setdefault("preserved_existing", []).append({
                    "number": number,
                    "reason": "new discovery differed from the previously verified mapping; existing mapping retained",
                })
            else:
                episode["audio_release"] = audio_release
    report["coverage_after"] = audio_release_coverage(episodes)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["duration_seconds"] = round(time.perf_counter() - run_started, 2)
    if write and report["verified"]:
        if catalogue_path.resolve() == CATALOGUE_PATH.resolve():
            write_catalogue(episodes, DATA_DIR)
        else:
            catalogue_path.write_text(
                json.dumps(episodes, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        report["catalogue_updated"] = True
        if catalogue_path.resolve() == CATALOGUE_PATH.resolve():
            scrape_report = {}
            try:
                if SCRAPE_REPORT_PATH.exists():
                    loaded_report = json.loads(SCRAPE_REPORT_PATH.read_text(encoding="utf-8"))
                    if isinstance(loaded_report, dict):
                        scrape_report = loaded_report
            except (OSError, json.JSONDecodeError):
                scrape_report = {}
            scrape_report["audio_release_coverage"] = report["coverage_after"]
            scrape_report["audio_enrichment"] = {
                "updated_at": report["finished_at"],
                "verified_count": len(report["verified"]),
                "failure_count": len(report["failures"]),
            }
            SCRAPE_REPORT_PATH.write_text(
                json.dumps(scrape_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    if report["failures"]:
        print(
            f"::warning::Audio discovery left {len(report['failures'])} episode(s) unresolved.",
            flush=True,
        )
    _write_github_step_summary(report)
    return report


def _write_github_step_summary(report: dict[str, Any]) -> None:
    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    if summary_path is None:
        return
    lines = [
        "## TKKG audio discovery",
        "",
        f"Targets: **{report['target_count']}**, verified: **{len(report['verified'])}**, "
        f"unresolved: **{len(report['failures'])}**",
        "",
    ]
    for item in report["verified"]:
        links = item["links"]
        lines.extend([
            f"### Episode {item['number']}: {item['title']}",
            f"- Spotify album: [open]({links['spotify_album']})",
            f"- YouTube Music source: "
            + (f"[playlist]({links['youtube_music_playlist']})" if links["youtube_music_playlist"]
               else f"[album]({links['youtube_music_album']})" if links.get("youtube_music_album")
               else "not verified"),
            f"- Stage timings: {item.get('timings', {})}",
            "",
            "| # | Track | Spotify | YouTube Music |",
            "|---:|---|---|---|",
        ])
        for spotify_track, ytm_track in zip(
            links["spotify_tracks"], links["youtube_music_tracks"], strict=True,
        ):
            lines.append(
                f"| {spotify_track['track_number']} | {spotify_track['title']} | "
                f"[open]({spotify_track['url']}) | [open]({ytm_track['url']}) |"
            )
        lines.append("")
    for item in report["failures"]:
        lines.extend([
            f"### Episode {item['number']}: {item['title']} unresolved",
            f"- Failed stage: {item['stage']}",
            f"- Reason: {item['error']}",
            f"- Stage timings: {item.get('timings', {})}",
        ])
        links = item.get("links")
        if links:
            lines.append(f"- Spotify album: [open]({links['spotify_album']})")
            lines.append("")
            lines.extend(["| # | Track | Spotify | YouTube Music |", "|---:|---|---|---|"])
            for track in links["spotify_tracks"]:
                lines.append(f"| {track['track_number']} | {track['title']} | [open]({track['url']}) | unresolved |")
        lines.append("")
    if report["failures"]:
        lines.extend(["**Warning:** one or more episodes remain unresolved. The workflow completed, but this is not an end-to-end success.", ""])
    summary_path.write_text("\n".join(lines), encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and verify Spotify/YouTube Music sources for TKKG episodes."
    )
    parser.add_argument("--episode", type=int, action="append", help="Episode number to process; may be repeated.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of missing episodes to process (default: 5).")
    parser.add_argument("--write", action="store_true", help="Save only successfully verified pairings to episodes.json. Default is dry-run.")
    parser.add_argument("--latest-first", action="store_true", help="Process the highest-numbered missing episodes first.")
    parser.add_argument("--playlist-id", help="Optional explicit YouTube Music playlist ID for verification or recovery.")
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE_PATH, help="Path to the episode JSON catalogue.")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="Path for the JSON run report.")
    args = parser.parse_args()

    try:
        episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
        if not isinstance(episodes, list):
            raise ValueError("Episode catalogue must be a JSON array.")
        if args.episode and any(number < 1 for number in args.episode):
            raise ValueError("Episode numbers must be positive.")
        if args.playlist_id and (not args.episode or len(args.episode) != 1):
            raise ValueError("--playlist-id requires exactly one --episode.")
        report = enrich_catalogue(
            episodes,
            selected_numbers=set(args.episode) if args.episode else None,
            limit=args.limit,
            write=args.write,
            catalogue_path=args.catalogue,
            latest_first=args.latest_first,
            playlist_id_override=args.playlist_id,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Audio discovery complete: {len(report['verified'])} verified, "
            f"{len(report['failures'])} unresolved.",
            flush=True,
        )
        for item in report["verified"]:
            links = item["links"]
            print(f"Episode {item['number']} Spotify album: {links['spotify_album']}", flush=True)
            if links["youtube_music_playlist"]:
                print(f"Episode {item['number']} YouTube Music playlist: {links['youtube_music_playlist']}", flush=True)
            elif links.get("youtube_music_album"):
                print(f"Episode {item['number']} YouTube Music album: {links['youtube_music_album']}", flush=True)
            for spotify_track, ytm_track in zip(
                links["spotify_tracks"], links["youtube_music_tracks"], strict=True,
            ):
                print(
                    f"  {spotify_track['track_number']:02d}. Spotify: {spotify_track['url']} | "
                    f"YouTube Music: {ytm_track['url']}",
                    flush=True,
                )
        for item in report["failures"]:
            if item.get("links"):
                print(f"Episode {item['number']} Spotify album: {item['links']['spotify_album']}", flush=True)
                for track in item["links"]["spotify_tracks"]:
                    print(f"  {track['track_number']:02d}. Spotify: {track['url']} | YouTube Music: unresolved", flush=True)
        return 0
    except Exception as exc:
        print(f"Audio discovery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
