import unittest
from unittest.mock import patch
from pathlib import Path

from scraper.audio_enrichment import resolve_spotify_album, SPOTIFY_ALBUM_BASE


def numbered_tracks(count, album_id, disc=1):
    return [
        {"name": f"Teil {i:02d}", "disc_number": disc, "track_number": i,
         "album_name": "Test release", "song_id": f"{i:022d}"[-22:]}
        for i in range(1, count + 1)
    ]


class SpotifyStructureResolverTests(unittest.TestCase):
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
