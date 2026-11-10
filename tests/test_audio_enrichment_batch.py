from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scraper.audio_enrichment_batch import aggregate, partition, select_episodes


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

    def test_missing_batch_report_blocks_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matrix = {"include": [{"batch": 0, "episodes": [1, 2]}]}
            report = aggregate(
                root / "episodes.json",
                root / "reports",
                json.dumps(matrix),
                write=True,
                discovery_result="success",
            )
        self.assertFalse(report["catalogue_updated"])
        self.assertEqual(report["missing_reports"], ["batch-0.json"])
        self.assertIn("publication_blocked", report)

    def _write_single_batch_report(self, root, result):
        reports = root / "reports"
        reports.mkdir()
        report = {
            "selected_numbers": [1],
            "target_count": 1,
            "verified": [result],
            "failures": [],
        }
        (reports / "batch-0.json").write_text(json.dumps(report), encoding="utf-8")
        return reports, json.dumps({"include": [{"batch": 0, "episodes": [1]}]})

    def test_dry_run_validates_without_writing_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalogue = root / "episodes.json"
            original = [{"number": 1}]
            catalogue.write_text(json.dumps(original), encoding="utf-8")
            result = {
                "number": 1,
                "audio_release": {"verification": {"status": "verified"}},
                "timings": {"total_seconds": 2.5},
            }
            reports, matrix = self._write_single_batch_report(root, result)
            with patch("scraper.audio_enrichment_batch.validate_catalogue", return_value=[]), \
                 patch("scraper.audio_enrichment_batch.write_catalogue") as write_catalogue:
                report = aggregate(
                    catalogue, reports, matrix, write=False, discovery_result="success",
                    max_parallel=4,
                )
            self.assertFalse(write_catalogue.called)
            self.assertEqual(json.loads(catalogue.read_text(encoding="utf-8")), original)
            self.assertEqual(report["max_parallel"], 4)
            self.assertEqual(report["episode_processing_seconds"], 2.5)
            self.assertGreaterEqual(report["duration_seconds"], 0)

    def test_existing_verified_mapping_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalogue = root / "episodes.json"
            existing = {"verification": {"status": "verified"}, "provider": "existing"}
            catalogue.write_text(json.dumps([{"number": 1, "audio_release": existing}]), encoding="utf-8")
            result = {
                "number": 1,
                "audio_release": {"verification": {"status": "verified"}, "provider": "new"},
                "timings": {"total_seconds": 1},
            }
            reports, matrix = self._write_single_batch_report(root, result)
            captured = {}
            def capture_write(episodes, output_dir):
                captured["episodes"] = episodes
            with patch("scraper.audio_enrichment_batch.validate_catalogue", return_value=[]), \
                 patch("scraper.audio_enrichment_batch.write_catalogue", side_effect=capture_write), \
                 patch("scraper.audio_enrichment_batch.audio_release_coverage", return_value={}):
                report = aggregate(
                    catalogue, reports, matrix, write=True, discovery_result="success",
                )
            self.assertTrue(report["catalogue_updated"])
            self.assertEqual(captured["episodes"][0]["audio_release"], existing)
            self.assertEqual(report["preserved_existing"][0]["number"], 1)

    def test_failed_discovery_matrix_blocks_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalogue = root / "episodes.json"
            result = {
                "number": 1,
                "audio_release": {"verification": {"status": "verified"}},
            }
            reports, matrix = self._write_single_batch_report(root, result)
            with patch("scraper.audio_enrichment_batch.write_catalogue") as write_catalogue:
                report = aggregate(
                    catalogue, reports, matrix, write=True, discovery_result="failure",
                )
            self.assertFalse(write_catalogue.called)
            self.assertFalse(report["catalogue_updated"])
            self.assertIn("publication_blocked", report)

    def test_partition_bounds(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 10"):
            partition([1, 2], 0)


if __name__ == "__main__":
    unittest.main()
