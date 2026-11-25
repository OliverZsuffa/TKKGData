from __future__ import annotations

import unittest

from scraper.audio_enrichment import enrich_catalogue


class AudioUnavailableRegistryTests(unittest.TestCase):
    def test_episode_128_is_reported_and_skipped_without_provider_requests(self):
        report = enrich_catalogue(
            [{"number": 128, "title": "Die Gehilfen des Terrors"}],
            selected_numbers={128},
        )

        self.assertEqual(report["selected_numbers"], [128])
        self.assertEqual(
            [item["number"] for item in report["known_unavailable"]],
            [128],
        )
        self.assertEqual(report["verified"], [])
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["coverage_after"]["known_unavailable"][0]["number"], 128)


if __name__ == "__main__":
    unittest.main()
