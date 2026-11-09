from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

from scraper.audio_enrichment import _load_ytmusic, resolve_spotify_album


EPISODE_150 = {"number": 150, "title": "Heiße Nächte im Dezember"}
DEFAULT_PLAYLIST_ID = "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"


def normalise(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"^\s*tkkg\s+", "", value)
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def compact_result(item: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "resultType", "category", "title", "videoId", "browseId",
        "playlistId", "audioPlaylistId", "artist", "artists",
        "duration", "duration_seconds", "album", "year", "isExplicit",
    )
    return {key: item[key] for key in keys if item.get(key) is not None}


def run_ytdlp(url: str) -> dict[str, Any]:
    try:
        import yt_dlp
    except ImportError as exc:
        return {"status": "unavailable", "error": f"yt-dlp import failed: {exc}"}

    options = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "playlistend": 100,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
        if not isinstance(info, dict):
            return {"status": "failed", "error": "yt-dlp returned no playlist metadata"}
        entries = info.get("entries") or []
        compact_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            compact_entries.append({
                key: entry.get(key)
                for key in (
                    "id", "title", "url", "webpage_url", "duration",
                    "artist", "artists", "album", "track", "playlist_index",
                )
                if entry.get(key) is not None
            })
        return {
            "status": "success",
            "extractor": info.get("extractor"),
            "title": info.get("title"),
            "id": info.get("id"),
            "playlist_count": info.get("playlist_count"),
            "entry_count": len(compact_entries),
            "entries": compact_entries,
        }
    except Exception as exc:
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic audio source experiments for one TKKG episode.")
    parser.add_argument("--episode", type=int, default=150)
    parser.add_argument("--playlist-id", default=DEFAULT_PLAYLIST_ID)
    parser.add_argument("--output", type=Path, default=Path("data/audio-source-experiment-report.json"))
    args = parser.parse_args()

    if args.episode != 150:
        parser.error("This first diagnostic fixture is intentionally limited to episode 150.")

    report: dict[str, Any] = {
        "episode": EPISODE_150,
        "playlist_id": args.playlist_id,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    try:
        with tempfile.TemporaryDirectory(prefix="tkkg_audio_experiment_") as temp:
            spotify = resolve_spotify_album(EPISODE_150, Path(temp))
        report["spotify"] = {
            "album_id": spotify["album_id"],
            "title": spotify["title"],
            "track_count": spotify["track_count"],
            "tracks": [
                {
                    "track_number": item.get("track_number"),
                    "title": item.get("name"),
                    "duration_seconds": item.get("duration"),
                    "artists": item.get("artists"),
                }
                for item in spotify["tracks"]
            ],
        }
    except Exception as exc:
        report["spotify"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    try:
        ytm = _load_ytmusic()
        query = "TKKG 150 Heiße Nächte im Dezember"
        raw_album_results = ytm.search(query, filter="albums", limit=10)
        raw_playlist_results = ytm.search(query, filter="playlists", limit=10)
        report["ytmusic_search"] = {
            "query": query,
            "albums": [compact_result(item) for item in raw_album_results if isinstance(item, dict)],
            "playlists": [compact_result(item) for item in raw_playlist_results if isinstance(item, dict)],
        }

        track_results = []
        for track in spotify["tracks"]:
            title = str(track["name"])
            time.sleep(0.4)
            try:
                results = ytm.search(title, filter="songs", limit=8)
                candidates = []
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    candidate = compact_result(item)
                    candidate_title = str(item.get("title") or "")
                    artists = item.get("artists") or []
                    artist_names = [
                        str(value.get("name", "")) if isinstance(value, dict) else str(value)
                        for value in artists
                    ]
                    candidate["title_exact_after_normalisation"] = normalise(candidate_title) == normalise(title)
                    candidate["artist_has_tkkg"] = any("tkkg" in name.casefold() for name in artist_names)
                    candidates.append(candidate)
                track_results.append({"spotify_title": title, "candidates": candidates})
            except Exception as exc:
                track_results.append({"spotify_title": title, "error": f"{type(exc).__name__}: {exc}"})
        report["individual_track_search"] = track_results
    except Exception as exc:
        report["ytmusic_search"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    playlist_url = f"https://music.youtube.com/playlist?list={args.playlist_id}"
    report["yt_dlp"] = {
        "music_url": run_ytdlp(playlist_url),
        "youtube_url": run_ytdlp(f"https://www.youtube.com/playlist?list={args.playlist_id}"),
    }
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
