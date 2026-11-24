import unittest
from unittest.mock import patch
from pathlib import Path

from scraper.audio_enrichment import resolve_spotify_album, SPOTIFY_ALBUM_BASE, _spotify_candidate_score


def numbered_tracks(count, album_id, disc=1):
    return [
        {"name": f"Teil {i:02d}", "disc_number": disc, "track_number": i,
         "album_name": "Test release", "song_id": f"{i:022d}"[-22:]}
        for i in range(1, count + 1)
    ]


class SpotifyStructureResolverTests(unittest.TestCase):
    def test_alternate_title_is_accepted_as_candidate_evidence(self):
        episode = {
            "number": 110,
            "title": "Das Phantom im Schokoladen-Museum",
            "alternate_titles": ["Das Phantom im Schokoladenmuseum"],
        }
        record = {
            "name": "110 - Das Phantom im Schokoladenmuseum - Teil 01",
            "artists": ["TKKG"],
            "album_name": "110/Das Phantom im Schokoladenmuseum",
            "search_query": "TKKG 110 Das Phantom im Schokoladenmuseum",
            "track_number": 1,
        }
        self.assertGreaterEqual(_spotify_candidate_score(episode, record), 100)

    @patch("scraper.audio_enrichment._save_spotify_metadata")
    def test_two_disc_override_returns_both_disc_sequences(self, fetch):
        tracks = numbered_tracks(40, "x", 1) + numbered_tracks(40, "x", 2)
        fetch.return_value = tracks
        result = resolve_spotify_album({"number": 175, "title": "Test"}, Path("."))
        fetch.assert_called_once_with(f"{SPOTIFY_ALBUM_BASE}7z37XBrYgYo7DCs9dFeHvq")
        self.assertEqual(result["track_count"], 80)
        self.assertEqual([t["disc_number"] for t in result["tracks"]].count(1), 40)
        self.assertEqual([t["disc_number"] for t in result["tracks"]].count(2), 40)
        self.assertEqual(result["source_query"], "configured_album_override")

    @patch("scraper.audio_enrichment._save_spotify_metadata")
    def test_configured_release_preserves_intro_and_outro_tracks(self, fetch):
        tracks = (
            numbered_tracks(40, "x", 1)
            + [{"name": "Intro", "disc_number": 1, "track_number": 41, "album_name": "Test release"}]
            + numbered_tracks(40, "x", 2)
            + [{"name": "Outsong", "disc_number": 2, "track_number": 41, "album_name": "Test release"}]
        )
        fetch.return_value = tracks
        result = resolve_spotify_album({"number": 175, "title": "Test"}, Path("."))
        self.assertEqual(result["track_count"], 82)
        self.assertEqual(result["tracks"][40]["name"], "Intro")
        self.assertEqual(result["tracks"][-1]["name"], "Outsong")
        self.assertEqual(
            [track["name"] for track in result["tracks"] if "Teil" in track["name"]][:2],
            ["Teil 01", "Teil 02"],
        )

    @patch("scraper.audio_enrichment._save_spotify_metadata")
    def test_expected_count_rejects_incomplete_album(self, fetch):
        fetch.return_value = numbered_tracks(39, "x", 1) + numbered_tracks(40, "x", 2)
        with self.assertRaisesRegex(ValueError, "expected 80"):
            resolve_spotify_album({"number": 175, "title": "Test"}, Path("."))

    @patch("scraper.audio_enrichment._save_spotify_metadata")
    def test_unknown_tracks_fail_closed(self, fetch):
        tracks = numbered_tracks(40, "x", 1) + numbered_tracks(40, "x", 2)
        tracks.append({"name": "Unidentified extra", "disc_number": 2, "track_number": 41})
        fetch.return_value = tracks
        with self.assertRaisesRegex(ValueError, "unclassified tracks"):
            resolve_spotify_album({"number": 175, "title": "Test"}, Path("."))

    @patch("scraper.audio_enrichment._save_spotify_metadata")
    def test_standard_override_uses_configured_album(self, fetch):
        fetch.return_value = numbered_tracks(80, "x", 1)
        result = resolve_spotify_album({"number": 200, "title": "Test"}, Path("."))
        fetch.assert_called_once_with(f"{SPOTIFY_ALBUM_BASE}40AzKKVoE6d4TxqlZ2N4Fr")
        self.assertEqual(result["track_count"], 80)


if __name__ == "__main__":
    unittest.main()
