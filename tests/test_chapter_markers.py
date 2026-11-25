from __future__ import annotations

import unittest

from scraper.audio_enrichment import _episode_title_matches_track
from scraper.spotify_structure import PART_RE, classify_track, validate_episode_parts


class ChapterMarkerTests(unittest.TestCase):
    def test_all_supported_chapter_markers_extract_the_number(self):
        for marker in ("Teil 01", "Part 01", "Kapitel 01", "KAPITEL 001"):
            with self.subTest(marker=marker):
                match = PART_RE.search(marker)
                self.assertIsNotNone(match)
                self.assertEqual(int(match.group(1)), 1)
                classified = classify_track({"name": f"226 - Der Täter ist unter uns - {marker}"})
                self.assertEqual(classified["classification"], "episode_part")
                self.assertEqual(classified["part_number"], 1)

    def test_variable_chapter_counts_are_accepted_without_a_fixed_limit(self):
        for count in (12, 20, 21, 31):
            with self.subTest(count=count):
                tracks = [
                    {"name": f"Kapitel {number:02d}: Nur Tote schlafen länger - Folge 238",
                     "track_number": number}
                    for number in range(1, count + 1)
                ]
                result = validate_episode_parts(tracks)
                self.assertTrue(result["valid"], result["errors"])
                self.assertEqual(len(result["parts"]), count)
                self.assertEqual(
                    [track["part_number"] for track in result["parts"]],
                    list(range(1, count + 1)),
                )

    def test_provider_chapter_counts_are_validated_independently(self):
        spotify = [
            {"name": f"Kapitel {number:02d}", "track_number": number}
            for number in range(1, 21)
        ]
        youtube_music = [
            {"name": f"Kapitel {number:02d}", "track_number": number}
            for number in range(1, 22)
        ]
        spotify_result = validate_episode_parts(spotify)
        ytm_result = validate_episode_parts(youtube_music)
        self.assertTrue(spotify_result["valid"], spotify_result["errors"])
        self.assertTrue(ytm_result["valid"], ytm_result["errors"])
        self.assertEqual(len(spotify_result["parts"]), 20)
        self.assertEqual(len(ytm_result["parts"]), 21)

    def test_duplicate_chapter_numbers_are_rejected(self):
        tracks = [
            {"name": "Kapitel 01", "track_number": 1},
            {"name": "Kapitel 01", "track_number": 2},
            {"name": "Kapitel 02", "track_number": 3},
        ]
        result = validate_episode_parts(tracks)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_missing_chapter_numbers_are_rejected(self):
        tracks = [
            {"name": "Kapitel 01", "track_number": 1},
            {"name": "Kapitel 03", "track_number": 2},
        ]
        result = validate_episode_parts(tracks)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_chapter_sequence_must_start_at_one(self):
        tracks = [
            {"name": "Kapitel 02", "track_number": 1},
            {"name": "Kapitel 03", "track_number": 2},
        ]
        result = validate_episode_parts(tracks)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_episode_226_alternate_title_matches_spotify_track(self):
        episode = {
            "number": 226,
            "title": "Der Täter unter uns",
            "alternate_titles": ["Der Täter ist unter uns"],
        }
        track = {
            "name": "226 - Der Täter ist unter uns - Teil 01",
            "album_name": "Folge 226: Der Täter ist unter uns",
        }
        self.assertTrue(_episode_title_matches_track(episode, track))


if __name__ == "__main__":
    unittest.main()
