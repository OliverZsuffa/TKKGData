from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scraper.audio_coverage_audit import audit, chunks, report_text
from scraper.audio_enrichment_batch import update_issue_ledger


class AudioCoverageAuditTests(unittest.TestCase):
    def test_classifies_missing_mapping_into_two_lists(self):
        episodes = [{"number": 1, "title": "A"}, {"number": 2, "title": "B"},
                    {"number": 3, "audio_release": {"verification": {"status": "verified"}}}]
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.json"
            ledger.write_text(json.dumps({"version": 1, "issues": {"2": {"reason": "failed"}}}))
            result = audit(episodes, ledger)
        self.assertEqual([x["number"] for x in result["ready_for_discovery"]], [1])
        self.assertEqual([x["number"] for x in result["needs_investigation"]], [2])

    def test_missing_ledger_warns_and_defaults_unrecorded_to_ready(self):
        result = audit([{"number": 1}], Path("missing-ledger-file.json"))
        self.assertIsNotNone(result["warning"])
        self.assertEqual([x["number"] for x in result["ready_for_discovery"]], [1])

    def test_corrupt_ledger_warns(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ledger.json"
            p.write_text("{broken")
            result = audit([{"number": 1}], p)
        self.assertIn("unreadable", result["warning"])

    def test_chunks_limit_batches_and_report_contains_selection(self):
        items = [{"number": n, "title": str(n)} for n in range(1, 22)]
        self.assertEqual([len(x) for x in chunks(items)], [10, 10, 1])
        result = {"ready_for_discovery": items, "needs_investigation": [], "warning": None}
        text = report_text(result)
        self.assertIn("**Episodes to paste into Discover:** " + ", ".join(str(n) for n in range(1, 22)), text)
        self.assertNotIn("Ready batch", text)

    def test_ledger_failure_updates_and_success_clears(self):
        episodes = [{"number": 1, "title": "One"}, {"number": 2, "title": "Two"}]
        failure = [{"number": 1, "title": "One", "stage": "youtube_music", "error": "unmatched"}]
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.json"
            update_issue_ledger(ledger, episodes, [], failure, [], [], timestamp="now")
            self.assertEqual(json.loads(ledger.read_text())["issues"]["1"]["reason"], "unmatched")
            update_issue_ledger(ledger, episodes, [{"number": 1}], [], [], [], timestamp="later")
            self.assertNotIn("1", json.loads(ledger.read_text())["issues"])

    def test_missing_batch_report_creates_issue(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.json"
            update_issue_ledger(ledger, [{"number": 8, "title": "Eight"}], [], [], ["batch-0.json"],
                               [{"batch": 0, "episodes": [8]}], timestamp="now")
            self.assertEqual(json.loads(ledger.read_text())["issues"]["8"]["category"], "batch_failure")


if __name__ == "__main__":
    unittest.main()
