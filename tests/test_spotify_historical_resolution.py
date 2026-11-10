from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from scraper.audio_enrichment import _spotify_artist_matches, resolve_spotify_album


class SpotifyHistoricalResolutionTests(unittest.TestCase):
    def test_exact_historical_artist_alias_is_allowed(self):
        self.assertTrue(_spotify_artist_matches({"artists": ["TKKG Retro-Archiv"]}))

    def test_artist_name_that_only_contains_tkkg_is_rejected(self):
        self.assertFalse(_spotify_artist_matches({"artists": ["TKKG Fanprojekt"]}))

    def test_compilation_selects_only_the_requested_episode_track(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        album_id = "A" * 22
        track_id = "B" * 22
        candidate = {
            "name": "20 - Das Geheimnis der alten Villa",
            "artists": ["TKKG Retro-Archiv"],
            "album_id": album_id,
            "album_name": "TKKG Hörspiel Sammlung",
            "track_number": 5,
            "song_id": track_id,
            "url": f"https://open.spotify.com/track/{track_id}",
            "search_query": "TKKG 20 Das Geheimnis der alten Villa",
        }
        album_tracks = [
            candidate,
            {
                "name": "21 - Die andere Folge",
                "artists": ["TKKG Retro-Archiv"],
                "album_id": album_id,
                "album_name": "TKKG Hörspiel Sammlung",
                "track_number": 6,
                "song_id": "C" * 22,
                "url": f"https://open.spotify.com/track/{'C' * 22}",
            },
        ]

        def fake_lookup(query):
            return album_tracks if query.endswith(album_id) else [candidate]

        with patch("scraper.audio_enrichment._save_spotify_metadata", side_effect=fake_lookup):
            result = resolve_spotify_album(episode, Path("."))

        self.assertEqual(result["album_id"], album_id)
        self.assertEqual(result["track_count"], 1)
        self.assertEqual(result["tracks"][0]["song_id"], track_id)
        self.assertEqual(result["release_type"], "compilation_track_selection")

    def test_ambiguous_equal_scoring_albums_are_rejected(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        first_album, second_album = "A" * 22, "B" * 22
        first_id, second_id = "C" * 22, "D" * 22

        def track(album_id, track_id):
            return {
                "name": "20 - Das Geheimnis der alten Villa Teil 01",
                "artists": ["TKKG"],
                "album_id": album_id,
                "album_name": "20 Das Geheimnis der alten Villa",
                "track_number": 1,
                "song_id": track_id,
                "url": f"https://open.spotify.com/track/{track_id}",
                "search_query": "TKKG 20 Das Geheimnis der alten Villa Teil 01",
            }

        candidates = [track(first_album, first_id), track(second_album, second_id)]

        def fake_lookup(query):
            if query.endswith(first_album):
                return [candidates[0]]
            if query.endswith(second_album):
                return [candidates[1]]
            return candidates

        with patch("scraper.audio_enrichment._save_spotify_metadata", side_effect=fake_lookup):
            with self.assertRaisesRegex(ValueError, "Ambiguous Spotify match"):
                resolve_spotify_album(episode, Path("."))


if __name__ == "__main__":
    unittest.main()
