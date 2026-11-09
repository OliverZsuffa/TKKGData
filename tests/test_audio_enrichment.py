from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from scraper.audio_enrichment import (
    _candidate_source,
    _track_titles_match,
    audio_release_coverage,
    enrich_catalogue,
    find_verified_youtube_music_playlist,
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
    "tracks": [
        {"name": "150 - Heiße Nächte im Dezember - Teil 01", "track_number": 1, "song_id": "0000000000000000000001", "url": "https://open.spotify.com/track/0000000000000000000001"},
        {"name": "150 - Heiße Nächte im Dezember - Teil 02", "track_number": 2, "song_id": "0000000000000000000002", "url": "https://open.spotify.com/track/0000000000000000000002"},
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
        result = find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        self.assertEqual(
            result["playlist_id"],
            "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        )
        self.assertEqual(result["track_count"], 2)
        self.assertTrue(result["url"].endswith("OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"))

    def test_album_search_browse_id_resolves_to_audio_playlist(self):
        ytm = FakeAlbumYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
        result = find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)
        self.assertEqual(ytm.asserted_browse_id, "MPREb_example")
        self.assertEqual(
            result["playlist_id"],
            "OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI",
        )

    def test_explicit_playlist_id_can_be_verified_without_search(self):
        ytm = FakeYTMusic(["OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI"])
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
        with self.assertRaisesRegex(ValueError, "No verified YouTube Music playlist"):
            find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)

    def test_multiple_verified_playlists_are_ambiguous(self):
        ytm = FakeYTMusic(["OLAK5uy_first123", "OLAK5uy_second123"])
        with self.assertRaisesRegex(ValueError, "Ambiguous YouTube Music match"):
            find_verified_youtube_music_playlist(EPISODE, SPOTIFY, ytm)

    def test_playlist_without_tkkg_artist_evidence_is_rejected(self):
        tracks = [
            {"title": item["name"], "artists": [{"name": "Unknown Artist"}]}
            for item in SPOTIFY["tracks"]
        ]
        ytm = FakeYTMusic(tracks=tracks, candidate_artist="Unknown Artist")
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

    def test_individual_song_search_rejects_uncorroborated_exact_title(self):
        candidates = {
            SPOTIFY["tracks"][0]["name"]: [{
                "videoId": "videoid0001",
                "title": SPOTIFY["tracks"][0]["name"],
                "artists": [{"name": "Unknown"}],
                "album": {"name": "Unrelated album"},
            }]
        }
        with self.assertRaisesRegex(ValueError, "No sufficiently corroborated"):
            find_verified_youtube_music_tracks(
                EPISODE, SPOTIFY, FakeSongSearchYTMusic(candidates),
            )

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
            "youtube_music": {"playlist_id": "OLAK5uy_example123"},
            "verification": {"status": "verified"},
        }
        with patch(
            "scraper.audio_enrichment.discover_episode_audio",
            return_value={"audio_release": fake_release, "matched_tracks": []},
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


if __name__ == "__main__":
    unittest.main()
