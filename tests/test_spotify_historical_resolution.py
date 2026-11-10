from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scraper.audio_enrichment import (
    _spotify_artist_album_records,
    _spotify_artist_ids,
    _spotify_artist_matches,
    discover_episode_audio,
    resolve_spotify_album,
)


class SpotifyHistoricalResolutionTests(unittest.TestCase):
    def test_artist_discography_finds_episode_in_compilation_box(self):
        artist_id, album_id, track_id = "A" * 22, "B" * 22, "C" * 22
        class FakeClient:
            def artist_albums(self, artist_id_arg, include_groups=None, limit=50, offset=0):
                self.call = (artist_id_arg, include_groups, limit, offset)
                return {
                    "items": [{"id": album_id, "name": "07/3er Box - Folge 19-21"}],
                    "total": 1,
                }
        client = FakeClient()
        fake_spotdl = types.ModuleType("spotdl")
        fake_spotdl.__path__ = []
        fake_utils = types.ModuleType("spotdl.utils")
        fake_utils.__path__ = []
        fake_spotify = types.ModuleType("spotdl.utils.spotify")
        fake_spotify.SpotifyClient = lambda: client
        album_tracks = [{
            "name": "TKKG (20) - Das Geheimnis der chinesischen Vase",
            "album_id": album_id,
            "album_name": "07/3er Box - Folge 19-21",
            "artists": ["TKKG"],
            "song_id": track_id,
            "url": "https://open.spotify.com/track/" + track_id,
        }]
        with patch("scraper.audio_enrichment._spotify_metadata_library", return_value=(None, None)), \
             patch("scraper.audio_enrichment._save_spotify_metadata", return_value=album_tracks), \
             patch.dict(sys.modules, {
                 "spotdl": fake_spotdl,
                 "spotdl.utils": fake_utils,
                 "spotdl.utils.spotify": fake_spotify,
             }):
            records = _spotify_artist_album_records(
                {artist_id}, {"number": 20, "title": "Das Geheimnis der chinesischen Vase"}
            )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["song_id"], track_id)
        self.assertIn("episode:20", records[0]["search_query"])
        self.assertEqual(client.call, (artist_id, "album,compilation", 50, 0))

    def test_artist_id_alignment_preserves_the_exact_credited_artist(self):
        self.assertEqual(
            _spotify_artist_ids({
                "artists": ["Guest Artist", "TKKG"],
                "artist_ids": ["", "B" * 22],
            }),
            {"B" * 22},
        )

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

    def test_episode_number_in_search_query_can_identify_unumbered_track_title(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        album_id, track_id = "A" * 22, "B" * 22
        candidate = {
            "name": "Das Geheimnis der alten Villa",
            "artists": ["TKKG Retro-Archiv"],
            "album_id": album_id,
            "album_name": "TKKG Hörspiel Sammlung",
            "track_number": 5,
            "song_id": track_id,
            "url": "https://open.spotify.com/track/" + track_id,
            "search_query": "TKKG 20 Das Geheimnis der alten Villa",
        }
        album_tracks = [
            candidate,
            {
                "name": "Die andere Folge",
                "artists": ["TKKG Retro-Archiv"],
                "album_id": album_id,
                "album_name": "TKKG Hörspiel Sammlung",
                "track_number": 6,
                "song_id": "C" * 22,
                "url": "https://open.spotify.com/track/" + "C" * 22,
            },
        ]
        def fake_lookup(query):
            return album_tracks if query.endswith(album_id) else [candidate]
        with patch("scraper.audio_enrichment._save_spotify_metadata", side_effect=fake_lookup):
            result = resolve_spotify_album(episode, Path("."))
        self.assertEqual(result["track_count"], 1)
        self.assertEqual(result["tracks"][0]["song_id"], track_id)

    def test_split_track_album_uses_episode_title_from_album_metadata(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        album_id = "A" * 22
        candidate = {
            "name": "Teil 01",
            "artists": ["TKKG"],
            "album_id": album_id,
            "album_name": "Folge 20: Das Geheimnis der alten Villa",
            "track_number": 1,
            "song_id": "B" * 22,
            "url": "https://open.spotify.com/track/" + "B" * 22,
            "search_query": "TKKG 20 Das Geheimnis der alten Villa",
        }
        album_tracks = [
            candidate,
            {
                "name": "Teil 02",
                "artists": ["TKKG"],
                "album_id": album_id,
                "album_name": "Folge 20: Das Geheimnis der alten Villa",
                "track_number": 2,
                "song_id": "C" * 22,
                "url": "https://open.spotify.com/track/" + "C" * 22,
            },
        ]
        def fake_lookup(query):
            return album_tracks if query.endswith(album_id) else [candidate]
        with patch("scraper.audio_enrichment._save_spotify_metadata", side_effect=fake_lookup):
            result = resolve_spotify_album(episode, Path("."))
        self.assertEqual(result["track_count"], 2)
        self.assertEqual(result["release_type"], "episode_release")

    def test_exact_title_search_can_match_without_number_in_track_or_query(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        album_id, track_id = "A" * 22, "B" * 22
        candidate = {
            "name": "Das Geheimnis der alten Villa",
            "artists": ["TKKG"],
            "album_id": album_id,
            "album_name": "TKKG Hörspiel Sammlung",
            "track_number": 5,
            "song_id": track_id,
            "url": "https://open.spotify.com/track/" + track_id,
            "search_query": 'track:"Das Geheimnis der alten Villa" artist:TKKG',
        }
        album_tracks = [candidate]
        def fake_lookup(query):
            return album_tracks if query.endswith(album_id) else [candidate]
        with patch("scraper.audio_enrichment._save_spotify_metadata", side_effect=fake_lookup):
            result = resolve_spotify_album(episode, Path("."))
        self.assertEqual(result["tracks"][0]["song_id"], track_id)

    def test_compilation_uses_individual_track_pairing_not_album_playlist(self):
        episode = {"number": 20, "title": "Das Geheimnis der alten Villa"}
        track_id = "B" * 22
        spotify = {
            "album_id": "A" * 22,
            "url": "https://open.spotify.com/album/" + "A" * 22,
            "title": "TKKG Hörspiel Sammlung",
            "track_count": 1,
            "source_query": "TKKG 20 Das Geheimnis der alten Villa",
            "release_type": "compilation_track_selection",
            "tracks": [{
                "name": "20 - Das Geheimnis der alten Villa",
                "track_number": 5,
                "song_id": track_id,
                "url": "https://open.spotify.com/track/" + track_id,
            }],
        }
        matched = [{
            "track_number": 1,
            "title": "20 - Das Geheimnis der alten Villa",
            "url": "https://music.youtube.com/watch?v=videoid0001",
            "spotify_track_url": "https://open.spotify.com/track/" + track_id,
            "match_evidence": ["exact_normalised_title"],
        }]
        with patch("scraper.audio_enrichment.resolve_spotify_album", return_value=spotify), \
             patch("scraper.audio_enrichment.find_verified_youtube_music_playlist", side_effect=AssertionError("must not pair a compilation album with a playlist")), \
             patch("scraper.audio_enrichment.find_verified_youtube_music_tracks", return_value=matched):
            result = discover_episode_audio(episode, object())

        self.assertIsNone(result["audio_release"]["youtube_music"]["playlist"])
        self.assertIsNone(result["links"]["youtube_music_playlist"])
        self.assertEqual(result["links"]["youtube_music_tracks"][0]["spotify_url"], "https://open.spotify.com/track/" + track_id)

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
