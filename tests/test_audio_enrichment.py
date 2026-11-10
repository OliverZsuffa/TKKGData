from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scraper.audio_enrichment import (
    AudioDiscoveryError,
    _candidate_source,
    _save_spotify_metadata,
    _track_titles_match,
    audio_release_coverage,
    enrich_catalogue,
    find_verified_youtube_music_playlist,
    discover_episode_audio,
    find_verified_youtube_music_tracks,
    preserve_verified_audio_releases,
    resolve_spotify_album,
)
from scraper.validate import validate_catalogue


EPISODE = {"number": 150, "title": "Heiße Nächte im Dezember"}
SPOTIFY = {
    "album_id": "0ZqyFeMXxCyIJvYptGlnn1",
    "url": "https://open.spotify.com/album/0ZqyFeMXxCyIJvYptGlnn1",
    "title": "150/Heiße Nächte im Dezember",
    "track_count": 2,
    "source_query": "TKKG 150 Heiße Nächte im Dezember Teil 01",
    "tracks": [
        {"name": "150 - Heiße Nächte im Dezember - Teil 01", "track_number": 1, "song_id": "0000000000000000000001", "url": "https://open.spotify.com/track/0000000000000000000001"},
        {"name": "150 - Heiße Nächte im Dezember - Teil 02", "track_number": 2, "song_id": "0000000000000000000002", "url": "https://open.spotify.com/track/0000000000000000000002"},
    ],
}


def ytdlp_playlist_info(playlist_id="OLAK5uy_example123", tracks=None):
    return {
        "id": playlist_id,
        "title": "Album - 150/Heiße Nächte im Dezember",
        "playlist_count": 2,
        "entries": tracks or [
            {"id": "videoid0001", "title": "150 - Heiße Nächte im Dezember (Teil 01)", "duration": 128},
            {"id": "videoid0002", "title": "150 - Heiße Nächte im Dezember (Teil 02)", "duration": 127},
        ],
    }


class FakeYTMusic:
    def __init__(self, playlist_ids=None, tracks=None, candidate_artist='TKKG'):
        self.playlist_ids = playlist_ids or ["OLAK5uy_example123"]
        self.candidate_artist = candidate_artist
        self.tracks = tracks or [
            {"title": "150 - Heiße Nächte im Dezember - Teil 01", "artists": [{"name": "TKKG"}]},
            {"title": "150 - Heiße Nächte im Dezember - Teil 02", "artists": [{"name": "TKKG"}]},
        ]
        self.search_calls = []

    def search(self, query, filter, limit):
        self.search_calls.append((query, filter, limit))
        return [
            {
                "resultType": "album",
                "playlistId": playlist_id,
                "title": "150/Heiße Nächte im Dezember",
                "artist": self.candidate_artist,
            }
            for playlist_id in self.playlist_ids
        ] if filter == "albums" else []

    def get_playlist(self, playlist_id, limit=None):
        return {
            "title": "150/Heiße Nächte im Dezember",
            "tracks": self.tracks,
        }


class FakeAlbumYTMusic(FakeYTMusic):
    def search(self, query, filter, limit):
        self.search_calls.append((query, filter, limit))
        if filter == "albums":
            return [{
                "resultType": "album",
                "browseId": "MPREb_example",
                "title": "150/Heiße Nächte im Dezember",
                "artists": [{"name": "TKKG"}],
            }]
        return []

    def get_album(self, browse_id):
        self.asserted_browse_id = browse_id
        return {
            "title": "150/Heiße Nächte im Dezember",
            "artists": [{"name": "TKKG"}],
            "audioPlaylistId": "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        }


class FakeSongSearchYTMusic:
    def __init__(self, candidates_by_title):
        self.candidates_by_title = candidates_by_title
        self.calls = []

    def search(self, query, filter, limit):
        self.calls.append((query, filter, limit))
        if filter != "songs":
            return []
        return self.candidates_by_title.get(query, [])




class FakeAlbumWithoutPlaylistYTMusic(FakeYTMusic):
    def search(self, query, filter, limit):
        self.search_calls.append((query, filter, limit))
        if filter == "albums":
            return [{
                "resultType": "album",
                "browseId": "MPREb_example",
                "title": "150/Heiße Nächte im Dezember",
                "artists": [{"name": "TKKG"}],
            }]
        return []

    def get_album(self, browse_id):
        self.asserted_browse_id = browse_id
        return {
            "title": "150/Heiße Nächte im Dezember",
            "artists": [{"name": "TKKG"}],
            "tracks": [
                {
                    "videoId": f"videoid{index:04d}",
                    "title": track["name"],
                    "duration_seconds": 128 - index,
                    "artists": [{"name": "TKKG"}],
                }
                for index, track in enumerate(SPOTIFY["tracks"], start=1)
            ],
        }


class AudioEnrichmentTests(unittest.TestCase):
    def test_official_audio_playlist_browse_id_is_recognized(self):
        source = _candidate_source(
            {"browseId": "VLOLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"},
            "playlists",
        )
        self.assertEqual(
            source,
            ("playlist", "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"),
        )

    def test_track_lists_must_match_exactly_in_order(self):
        self.assertTrue(_track_titles_match(SPOTIFY["tracks"], FakeYTMusic().tracks))
        reversed_tracks = list(reversed(FakeYTMusic().tracks))
        self.assertFalse(_track_titles_match(SPOTIFY["tracks"], reversed_tracks))

    def test_known_episode_150_playlist_id_is_discovered_and_verified(self):
        ytm = FakeYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI")):
            result = find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        self.assertEqual(
            result["playlist_id"],
            "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        )
        self.assertEqual(result["track_count"], 2)
        self.assertTrue(result["url"].endswith("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"))

    def test_album_search_browse_id_resolves_to_audio_playlist(self):
        ytm = FakeAlbumYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI")):
            result = find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        self.assertEqual(ytm.asserted_browse_id, "MPREb_example")
        self.assertEqual(
            result["playlist_id"],
            "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        )


    def test_album_tracklist_is_verified_when_no_public_playlist_id_exists(self):
        ytm = FakeAlbumWithoutPlaylistYTMusic()
        with patch(
            "scraper.audio_enrichment._extract_ytdlp_playlist",
            side_effect=AssertionError("No playlist extraction should be attempted"),
        ):
            result = find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        self.assertIsNone(result["playlist_id"])
        self.assertEqual(result["album_id"], "MPREb_example")
        self.assertEqual(result["album_url"], "https://music.youtube.com/browse/MPREb_example")
        self.assertEqual(len(result["_matched_tracks"]), 2)
        self.assertIn("ordered_album_match", result["_matched_tracks"][0]["match_evidence"])

    def test_discovery_returns_album_page_and_ordered_song_links_without_playlist_id(self):
        ytm = FakeAlbumWithoutPlaylistYTMusic()
        with patch("scraper.audio_enrichment.resolve_spotify_album", return_value=SPOTIFY):
            result = discover_episode_audio(EPISODE, ytm)
        self.assertIsNone(result["audio_release"]["youtube_music"]["playlist"])
        self.assertEqual(
            result["links"]["youtube_music_album"],
            "https://music.youtube.com/browse/MPREb_example",
        )
        self.assertEqual(len(result["links"]["youtube_music_tracks"]), 2)
        self.assertEqual(
            result["audio_release"]["verification"]["method"],
            "exact_ordered_album_track_titles_and_duration",
        )


    def test_explicit_ytdlp_playlist_is_verified_and_produces_individual_links(self):
        playlist_id = "OLAK5uy_example123"
        info = {
            "id": playlist_id,
            "title": "Album - 150/Heiße Nächte im Dezember",
            "playlist_count": 2,
            "entries": [
                {"id": "videoid0001", "title": "150 - Heiße Nächte im Dezember (Teil 01)", "url": "https://music.youtube.com/watch?v=videoid0001", "duration": 128},
                {"id": "videoid0002", "title": "150 - Heiße Nächte im Dezember (Teil 02)", "url": "https://music.youtube.com/watch?v=videoid0002", "duration": 127},
            ],
        }
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=info):
            result = find_verified_youtube_music_playlist(
                EPISODE, SPOTIFY, FakeYTMusic(), playlist_id,
            )
        self.assertEqual(result["playlist_id"], playlist_id)
        self.assertEqual(result["track_count"], 2)
        self.assertEqual(result["_matched_tracks"][0]["video_id"], "videoid0001")
        self.assertEqual(result["_matched_tracks"][0]["spotify_track_url"], SPOTIFY["tracks"][0]["url"])

    def test_explicit_ytdlp_playlist_rejects_wrong_track_order(self):
        playlist_id = "OLAK5uy_example123"
        info = {
            "id": playlist_id,
            "title": "Album - 150/Heiße Nächte im Dezember",
            "playlist_count": 2,
            "entries": [
                {"id": "videoid0002", "title": "150 - Heiße Nächte im Dezember (Teil 02)", "duration": 127},
                {"id": "videoid0001", "title": "150 - Heiße Nächte im Dezember (Teil 01)", "duration": 128},
            ],
        }
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=info):
            with self.assertRaisesRegex(ValueError, "does not match Spotify track"):
                find_verified_youtube_music_playlist(
                    EPISODE, SPOTIFY, FakeYTMusic(), playlist_id,
                )

    def test_discover_uses_verified_playlist_entries_without_song_search(self):
        playlist_id = "OLAK5uy_example123"
        info = {
            "id": playlist_id,
            "title": "Album - 150/Heiße Nächte im Dezember",
            "playlist_count": 2,
            "entries": [
                {"id": "videoid0001", "title": "150 - Heiße Nächte im Dezember (Teil 01)", "duration": 128},
                {"id": "videoid0002", "title": "150 - Heiße Nächte im Dezember (Teil 02)", "duration": 127},
            ],
        }
        ytm = FakeYTMusic()
        with patch("scraper.audio_enrichment.resolve_spotify_album", return_value=SPOTIFY), \
             patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=info):
            result = discover_episode_audio(EPISODE, ytm, playlist_id)
        self.assertEqual(len(result["audio_release"]["youtube_music"]["tracks"]), 2)
        self.assertEqual(result["audio_release"]["verification"]["method"], "exact_ordered_playlist_track_titles_and_duration")
        self.assertEqual(result["links"]["spotify_album"], SPOTIFY["url"])
        self.assertEqual(len(result["links"]["spotify_tracks"]), 2)
        self.assertEqual(result["links"]["youtube_music_playlist"], f"https://music.youtube.com/playlist?list={playlist_id}")
        self.assertEqual(len(result["links"]["youtube_music_tracks"]), 2)
        self.assertIn("spotify_seconds", result["timings"])
        self.assertIn("playlist_seconds", result["timings"])
        self.assertIn("total_seconds", result["timings"])
        self.assertEqual(ytm.search_calls, [])

    def test_explicit_playlist_id_can_be_verified_without_search(self):
        ytm = FakeYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI")):
            result = find_verified_youtube_music_playlist(
                EPISODE,
                SPOTIFY,
                ytm,
                "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
            )
        self.assertEqual(
            result["playlist_id"],
            "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        )
        self.assertEqual(ytm.search_calls, [])

    def test_wrong_track_list_is_rejected(self):
        ytm = FakeYTMusic(tracks=[
            {"title": "150 - Heiße Nächte im Dezember - Teil 01", "artists": [{"name": "TKKG"}]},
            {"title": "An unrelated recording", "artists": [{"name": "TKKG"}]},
        ])
        wrong_entries = [
            {"id": "videoid0001", "title": "150 - Heiße Nächte im Dezember - Teil 01"},
            {"id": "videoid0002", "title": "An unrelated recording"},
        ]
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info(tracks=wrong_entries)):
            with self.assertRaisesRegex(ValueError, "No verified YouTube Music playlist"):
                find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)

    def test_multiple_verified_playlists_are_ambiguous(self):
        ytm = FakeYTMusic(["OLAK5uy_first123", "OLAK5uy_second123"])
        def extract(url):
            from urllib.parse import parse_qs, urlparse
            playlist_id = parse_qs(urlparse(url).query)["list"][0]
            return ytdlp_playlist_info(playlist_id)
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", side_effect=extract):
            with self.assertRaisesRegex(ValueError, "Ambiguous YouTube Music match"):
                find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)

    def test_playlist_without_tkkg_artist_evidence_is_rejected(self):
        tracks = [
            {"title": item["name"], "artists": [{"name": "Unknown Artist"}]}
            for item in SPOTIFY["tracks"]
        ]
        ytm = FakeYTMusic(tracks=tracks, candidate_artist="Unknown Artist")
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info()):
            with self.assertRaisesRegex(ValueError, "No verified YouTube Music playlist"):
                find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)

    def test_spotify_album_count_comes_from_actual_track_records(self):
        first_track = [{
            "name": "150 - Heiße Nächte im Dezember - Teil 01",
            "artists": ["TKKG"],
            "album_id": SPOTIFY["album_id"],
            "album_name": SPOTIFY["title"],
        }]
        album_tracks = [
            {**track, "album_id": SPOTIFY["album_id"]}
            for track in SPOTIFY["tracks"]
        ]
        with patch(
            "scraper.audio_enrichment._save_spotify_metadata",
            side_effect=[first_track, album_tracks],
        ):
            result = resolve_spotify_album(EPISODE, Path("."))
        self.assertEqual(result["track_count"], 2)

    def test_previous_verified_mapping_survives_empty_refresh(self):
        old = {
            "spotify": {"album_id": "a" * 22},
            "youtube_music": {"playlist_id": "OLAK5uy_example123"},
            "verification": {"status": "verified"},
        }
        refreshed = [{"number": 150, "title": EPISODE["title"]}]
        conflicts = preserve_verified_audio_releases(
            refreshed,
            [{"number": 150, "audio_release": old}],
        )
        self.assertEqual(conflicts, [])
        self.assertEqual(refreshed[0]["audio_release"], old)

    def test_previous_verified_mapping_wins_on_conflict(self):
        old = {"verification": {"status": "verified"}, "source": "old"}
        changed = {"verification": {"status": "verified"}, "source": "new"}
        refreshed = [{"number": 150, "audio_release": changed}]
        conflicts = preserve_verified_audio_releases(
            refreshed,
            [{"number": 150, "audio_release": old}],
        )
        self.assertEqual(refreshed[0]["audio_release"], old)
        self.assertEqual(len(conflicts), 1)

    def test_schema_and_cross_provider_counts_validate(self):
        episode = {
            "number": 150, "title": EPISODE["title"], "series": "TKKG",
            "synopsis": None, "cover_url": None, "release_date": None, "release_year": None,
            "physical_releases": [], "tracks": [], "cast": [], "credits": [], "ratings": [],
            "sources": [{"name": "test", "url": "https://example.com", "retrieved_at": "2026-11-09T00:00:00Z"}],
            "last_checked": "2026-11-09T00:00:00Z", "listening_links": [],
            "audio_release": {
                "spotify": {
                    "album_id": "0ZqyFeMXxCyIJvYptGlnn1",
                    "url": "https://open.spotify.com/album/0ZqyFeMXxCyIJvYptGlnn1",
                    "title": "150/Heiße Nächte im Dezember", "track_count": 2,
                    "source_query": "TKKG 150 Heiße Nächte im Dezember Teil 01",
                },
                "youtube_music": {
                    "playlist": {
                        "playlist_id": "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
                        "url": "https://music.youtube.com/playlist?list=OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
                        "title": "150/Heiße Nächte im Dezember", "track_count": 2,
                    },
                    "tracks": [
                        {"track_number": 1, "spotify_title": SPOTIFY["tracks"][0]["name"], "spotify_track_id": SPOTIFY["tracks"][0]["song_id"], "spotify_track_url": SPOTIFY["tracks"][0]["url"], "video_id": "videoid0001", "url": "https://music.youtube.com/watch?v=videoid0001", "title": SPOTIFY["tracks"][0]["name"], "artists": ["TKKG"], "album": "150/Heiße Nächte im Dezember", "duration_seconds": 120, "match_score": 140, "match_evidence": ["exact_normalised_title", "episode_album"]},
                        {"track_number": 2, "spotify_title": SPOTIFY["tracks"][1]["name"], "spotify_track_id": SPOTIFY["tracks"][1]["song_id"], "spotify_track_url": SPOTIFY["tracks"][1]["url"], "video_id": "videoid0002", "url": "https://music.youtube.com/watch?v=videoid0002", "title": SPOTIFY["tracks"][1]["name"], "artists": ["TKKG"], "album": "150/Heiße Nächte im Dezember", "duration_seconds": 120, "match_score": 140, "match_evidence": ["exact_normalised_title", "episode_album"]},
                    ],
                    "track_count": 2,
                },
                "verification": {
                    "status": "verified", "verified_at": "2026-11-09T00:00:00Z",
                    "method": "test", "matched_track_count": 2,
                    "playlist_status": "verified", "playlist_error": None,
                },
            },
        }
        self.assertEqual(validate_catalogue([episode]), [])
        episode["audio_release"]["youtube_music"]["track_count"] = 3
        self.assertTrue(any("track counts differ" in error for error in validate_catalogue([episode])))


    def test_individual_song_links_are_resolved_with_album_evidence(self):
        candidates = {
            track["name"]: [{
                "videoId": f"videoid{index:04d}",
                "title": track["name"],
                "artists": [{"name": "Europa"}],
                "album": {"name": SPOTIFY["title"]},
                "duration_seconds": 120,
            }]
            for index, track in enumerate(SPOTIFY["tracks"], start=1)
        }
        result = find_verified_youtube_music_tracks(
            EPISODE, SPOTIFY, FakeSongSearchYTMusic(candidates),
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["url"].startswith("https://music.youtube.com/watch?v=") for item in result))
        self.assertTrue(all(item["spotify_track_url"].startswith("https://open.spotify.com/track/") for item in result))
        self.assertTrue(all("episode_album" in item["match_evidence"] for item in result))


    def test_individual_song_search_tries_tkkg_specific_query_variants(self):
        title = SPOTIFY["tracks"][0]["name"]
        candidate = {
            "videoId": "videoid0001",
            "title": title,
            "artists": [{"name": "TKKG"}],
            "album": {"name": SPOTIFY["title"]},
            "duration_seconds": 120,
        }
        ytm = FakeSongSearchYTMusic({f"TKKG {title}": [candidate]})
        result = find_verified_youtube_music_tracks(EPISODE, SPOTIFY, ytm)
        self.assertEqual(result[0]["video_id"], "videoid0001")
        self.assertIn(f"TKKG {title}", [query for query, _, _ in ytm.calls])
        self.assertIn(
            "TKKG Folge 150 Heiße Nächte im Dezember Teil 01",
            [query for query, _, _ in ytm.calls],
        )


    def test_individual_song_mapping_requires_valid_spotify_track_identity(self):
        spotify = {**SPOTIFY, "tracks": [{**SPOTIFY["tracks"][0], "song_id": "invalid", "url": "not-a-spotify-url"}]}
        candidates = {
            spotify["tracks"][0]["name"]: [{
                "videoId": "videoid0001",
                "title": spotify["tracks"][0]["name"],
                "artists": [{"name": "Europa"}],
                "album": {"name": SPOTIFY["title"]},
                "duration_seconds": 120,
            }]
        }
        with self.assertRaisesRegex(ValueError, "no valid track ID"):
            find_verified_youtube_music_tracks(
                EPISODE, spotify, FakeSongSearchYTMusic(candidates),
            )

    def test_individual_song_search_rejects_uncorroborated_exact_title(self):
        candidates = {
            SPOTIFY["tracks"][0]["name"]: [{
                "videoId": "videoid0001",
                "title": SPOTIFY["tracks"][0]["name"],
                "artists": [{"name": "Unknown"}],
                "album": {"name": "Unrelated album"},
            }]
        }
        with self.assertRaisesRegex(ValueError, "No sufficiently corroborated") as caught:
            find_verified_youtube_music_tracks(
                EPISODE, SPOTIFY, FakeSongSearchYTMusic(candidates),
            )
        self.assertIn("Candidate diagnostics", str(caught.exception))
        self.assertIn('"score": 100', str(caught.exception))
        self.assertIn("score below unchanged threshold of 130", str(caught.exception))

    def test_individual_song_search_rejects_ambiguous_matches(self):
        title = SPOTIFY["tracks"][0]["name"]
        candidates = {
            title: [
                {"videoId": "videoid0001", "title": title, "artists": [{"name": "TKKG"}]},
                {"videoId": "videoid0002", "title": title, "artists": [{"name": "TKKG"}]},
            ]
        }
        with self.assertRaisesRegex(ValueError, "Ambiguous YouTube Music song match"):
            find_verified_youtube_music_tracks(
                EPISODE, SPOTIFY, FakeSongSearchYTMusic(candidates),
            )


    def test_latest_first_batch_selects_highest_missing_episode_numbers(self):
        episodes = [
            {"number": 1, "title": "One"},
            {"number": 2, "title": "Two"},
            {"number": 3, "title": "Three"},
        ]
        fake_release = {
            "spotify": {"track_count": 1},
            "youtube_music": {"playlist": None, "track_count": 1},
            "verification": {"status": "verified"},
        }
        with patch(
            "scraper.audio_enrichment.discover_episode_audio",
            return_value={
                "audio_release": fake_release,
                "matched_tracks": [],
                "links": {
                    "spotify_album": "https://open.spotify.com/album/" + "a" * 22,
                    "spotify_tracks": [],
                    "youtube_music_playlist": None,
                    "youtube_music_tracks": [],
                },
                "timings": {"total_seconds": 0.01},
            },
        ):
            report = enrich_catalogue(episodes, limit=2, latest_first=True, ytm=object())
        self.assertEqual([item["number"] for item in report["verified"]], [3, 2])

    def test_coverage_counts_verified_and_missing_records(self):
        episodes = [
            {"number": 1, "title": "A", "audio_release": {"verification": {"status": "verified"}}},
            {"number": 2, "title": "B"},
        ]
        coverage = audio_release_coverage(episodes)
        self.assertEqual(coverage["verified_pairings"], 1)
        self.assertEqual(coverage["missing_pairings"], [{"number": 2, "title": "B"}])


    def test_spotify_metadata_library_works_without_ffmpeg_in_path(self):
        class FakeSong:
            @classmethod
            def from_search_term(cls, query):
                cls.query = query
                return type("SongRecord", (), {"json": {"name": "First track"}})()

        class FakeAlbum:
            @classmethod
            def from_url(cls, url, fetch_songs=False):
                cls.call = (url, fetch_songs)
                return type("AlbumRecord", (), {
                    "songs": [type("TrackRecord", (), {"json": {"name": "Track 1"}})()]
                })()

        with tempfile.TemporaryDirectory() as empty_path:
            with patch("scraper.audio_enrichment._spotify_metadata_library", return_value=(FakeSong, FakeAlbum)):
                with patch.dict(os.environ, {"PATH": empty_path}):
                    first = _save_spotify_metadata("TKKG 150 Heiße Nächte im Dezember Teil 01")
                    album = _save_spotify_metadata(SPOTIFY["url"])
        self.assertEqual(first, [{"name": "First track"}])
        self.assertEqual(album, [{"name": "Track 1"}])
        self.assertEqual(FakeSong.query, "TKKG 150 Heiße Nächte im Dezember Teil 01")
        self.assertEqual(FakeAlbum.call, (SPOTIFY["url"], False))

    def test_playlist_discovery_searches_spotify_album_and_track_metadata(self):
        ytm = FakeYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
        with patch("scraper.audio_enrichment._extract_ytdlp_playlist", return_value=ytdlp_playlist_info("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI")):
            find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        queries = [query for query, _, _ in ytm.search_calls]
        self.assertIn(SPOTIFY["title"], queries)
        self.assertIn(f"TKKG {SPOTIFY['title']}", queries)
        self.assertIn(f"TKKG {SPOTIFY['tracks'][0]['name']}", queries)

    def test_discovery_failure_preserves_spotify_links_and_playlist_error(self):
        class NoResultsYTMusic:
            def search(self, query, filter, limit):
                return []

        with patch("scraper.audio_enrichment.resolve_spotify_album", return_value=SPOTIFY):
            with self.assertRaises(AudioDiscoveryError) as caught:
                discover_episode_audio(EPISODE, NoResultsYTMusic())
        error = caught.exception
        self.assertEqual(error.stage, "youtube_music")
        self.assertEqual(error.spotify["url"], SPOTIFY["url"])
        self.assertIn("No verified YouTube Music playlist", error.playlist_error)
        self.assertIn("Complete playlist discovery also failed", str(error))

    def test_unresolved_report_keeps_verified_spotify_links(self):
        with patch(
            "scraper.audio_enrichment.discover_episode_audio",
            side_effect=AudioDiscoveryError(
                "YouTube Music unresolved", stage="youtube_music",
                spotify=SPOTIFY, playlist_error="No playlist candidate",
            ),
        ):
            report = enrich_catalogue([dict(EPISODE)], ytm=object())
        failure = report["failures"][0]
        self.assertEqual(failure["stage"], "youtube_music")
        self.assertEqual(failure["links"]["spotify_album"], SPOTIFY["url"])
        self.assertEqual(len(failure["links"]["spotify_tracks"]), 2)
        self.assertIsNone(failure["links"]["youtube_music_playlist"])

    def test_audio_workflow_has_no_episode_specific_or_ffmpeg_setup(self):
        workflow = Path(".github/workflows/audio-enrichment.yml").read_text(encoding="utf-8")
        self.assertNotIn("150", workflow)
        self.assertNotIn("ffmpeg", workflow.casefold())
        self.assertNotIn("push:", workflow)
        self.assertIn('default: ""', workflow)
        self.assertIn("playlist_id:", workflow)

    def test_live_integration_workflow_covers_148_149_150(self):
        workflow = Path(".github/workflows/audio-enrichment-integration.yml").read_text(encoding="utf-8")
        self.assertIn("episode: [148, 149, 150]", workflow)
        self.assertIn("--episode", workflow)
        self.assertNotIn("--playlist-id", workflow)



    def test_explicit_episode_lookup_rechecks_existing_verified_mapping(self):
        existing = {
            "spotify": {"album_id": "a" * 22},
            "youtube_music": {"tracks": []},
            "verification": {"status": "verified"},
        }
        episode = {**EPISODE, "audio_release": existing}
        fake_release = {
            "spotify": {"track_count": 2},
            "youtube_music": {"playlist": None, "tracks": [], "track_count": 2},
            "verification": {"status": "verified"},
        }
        fake_discovery = {
            "audio_release": fake_release,
            "matched_tracks": [],
            "links": {
                "spotify_album": SPOTIFY["url"],
                "spotify_tracks": [],
                "youtube_music_playlist": None,
                "youtube_music_tracks": [],
            },
            "timings": {"total_seconds": 0.01},
        }
        with patch("scraper.audio_enrichment.discover_episode_audio", return_value=fake_discovery) as discover:
            report = enrich_catalogue(
                [episode], selected_numbers={150}, limit=1, ytm=object(),
            )
        discover.assert_called_once()
        self.assertEqual(report["target_count"], 1)
        self.assertEqual(len(report["verified"]), 1)
        self.assertEqual(episode["audio_release"], existing)



    def test_explicit_episode_lookup_rechecks_existing_verified_mapping(self):
        existing = {
            "spotify": {"album_id": "a" * 22},
            "youtube_music": {"tracks": []},
            "verification": {"status": "verified"},
        }
        episode = {**EPISODE, "audio_release": existing}
        fake_release = {
            "spotify": {"track_count": 2},
            "youtube_music": {"playlist": None, "tracks": [], "track_count": 2},
            "verification": {"status": "verified"},
        }
        fake_discovery = {
            "audio_release": fake_release,
            "matched_tracks": [],
            "links": {
                "spotify_album": SPOTIFY["url"],
                "spotify_tracks": [],
                "youtube_music_playlist": None,
                "youtube_music_tracks": [],
            },
            "timings": {"total_seconds": 0.01},
        }
        with patch("scraper.audio_enrichment.discover_episode_audio", return_value=fake_discovery) as discover:
            report = enrich_catalogue(
                [episode], selected_numbers={150}, limit=1, ytm=object(),
            )
        discover.assert_called_once()
        self.assertEqual(report["target_count"], 1)
        self.assertEqual(len(report["verified"]), 1)
        self.assertEqual(episode["audio_release"], existing)



if __name__ == "__main__":
    unittest.main()
