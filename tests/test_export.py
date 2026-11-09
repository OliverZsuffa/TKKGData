from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scraper.export import CSV_FIELDS, write_catalogue


class CatalogueExportTests(unittest.TestCase):
    def test_csv_includes_schema_required_series_field(self):
        episode = {
            "number": 1,
            "series": "TKKG",
            "title": "Die Jagd nach den Millionendieben",
            "synopsis": None,
            "cover_url": None,
            "release_date": None,
            "release_year": 1981,
            "physical_releases": [],
            "tracks": [],
            "cast": [],
            "credits": [],
            "ratings": [],
            "sources": [{
                "name": "Official TKKG catalogue",
                "url": "https://www.tkkg.de/produkte/details/test",
                "retrieved_at": "2026-10-18T00:00:00+00:00",
            }],
            "last_checked": "2026-10-18T00:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            write_catalogue([episode], output_dir)
            with (output_dir / "episodes.csv").open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                fieldnames = reader.fieldnames
            payload = json.loads((output_dir / "episodes.json").read_text(encoding="utf-8"))

        self.assertIn("series", CSV_FIELDS)
        self.assertIn("series", fieldnames)
        self.assertEqual(rows[0]["series"], "TKKG")
        self.assertEqual(payload[0]["series"], "TKKG")


if __name__ == "__main__":
    unittest.main()
