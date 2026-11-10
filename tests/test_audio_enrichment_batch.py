from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scraper.audio_enrichment_batch import partition, select_episodes


class AudioEnrichmentBatchTests(unittest.TestCase):
    def setUp(self):
        self.episodes = [
            {"number": 1},
            {"number": 2, "audio_release": {"verification": {"status": "verified"}}},
            {"number": 3},
            {"number": 4},
            {"number": 5},
            {"number": 6},
        ]

    def test_inclusive_range(self):
        self.assertEqual(
            select_episodes(self.episodes, start_episode=2, end_episode=5),
            [2, 3, 4, 5],
        )

    def test_single_episode(self):
        self.assertEqual(select_episodes(self.episodes, episode=3), [3])

    def test_missing_defaults_to_latest_five(self):
        self.assertEqual(select_episodes(self.episodes), [6, 5, 4, 3, 1])

    def test_partial_range_rejected(self):
        with self.assertRaisesRegex(ValueError, "Both range bounds"):
            select_episodes(self.episodes, start_episode=1)

    def test_reversed_range_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            select_episodes(self.episodes, start_episode=5, end_episode=2)

    def test_unknown_episode_rejected(self):
        with self.assertRaisesRegex(ValueError, "not present"):
            select_episodes(self.episodes, episode=99)

    def test_cannot_mix_single_and_range(self):
        with self.assertRaisesRegex(ValueError, "either --episode"):
            select_episodes(self.episodes, episode=1, start_episode=1, end_episode=2)

    def test_partition_covers_every_episode_once(self):
        selected = list(range(1, 244))
        batches = partition(selected, 5)
        flattened = [item for batch in batches for item in batch]
        self.assertEqual(flattened, selected)
        self.assertEqual(len(batches), 49)
        self.assertEqual(len(batches[-1]), 3)

    def test_partition_bounds(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 10"):
            partition([1, 2], 0)


if __name__ == "__main__":
    unittest.main()
