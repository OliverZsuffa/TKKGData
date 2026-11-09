from __future__ import annotations

import unittest

from scraper.merge import merge_records
from scraper.validate import validate_catalogue


def episode(number: int, title: str, cast: list[dict], source_name: str) -> dict:
    return {
        "number": number,
        "title": title,
        "series": "TKKG",
        "synopsis": None,
        "cover_url": None,
        "release_date": None,
        "release_year": None,
        "physical_releases": [],
        "tracks": [],
        "cast": cast,
        "credits": [],
        "ratings": [],
        "listening_links": [],
        "sources": [{
            "name": source_name,
            "url": "https://example.com/episode",
            "retrieved_at": "2026-10-18T00:00:00+00:00",
        }],
        "last_checked": "2026-10-18T00:00:00+00:00",
    }


class MergeCastTests(unittest.TestCase):
    def test_archive_cast_is_preferred_instead_of_unioning_official_cast(self):
        archive_cast = [
            {"name": "Wolfgang Kaven", "character": "Erzähler"},
            {"name": "Sascha Draeger", "character": "Tim / Tarzan / Peter Carsten"},
        ]
        official_cast = [
            {"name": "Wolfgang Kaven", "character": "Erzähler"},
            {"name": "Sascha Draeger", "character": "Tim"},
            {"name": "Niki Nowotny", "character": "Karl"},
        ]
        merged, conflicts = merge_records([
            episode(1, "Testfolge", archive_cast, "TKKG-Site archive"),
            episode(1, "Testfolge", official_cast, "Official TKKG catalogue"),
        ])
        self.assertEqual(conflicts, [])
        self.assertEqual(merged[0]["cast"], archive_cast)

    def test_official_cast_is_used_when_preferred_source_has_no_cast(self):
        official_cast = [{"name": "Sascha Draeger", "character": "Tim"}]
        merged, _ = merge_records([
            episode(1, "Testfolge", [], "TKKG-Site archive"),
            episode(1, "Testfolge", official_cast, "Official TKKG catalogue"),
        ])
        self.assertEqual(merged[0]["cast"], official_cast)

    def test_official_listening_url_hostname_is_case_insensitive(self):
        record = episode(1, "Testfolge", [], "test")
        record["listening_links"] = [{
            "service": "official",
            "label": "Official listening page",
            "url": "https://TKKG.lnk.to/-001AW",
            "link_type": "official_hub",
            "source_url": "https://www.tkkg.de/produkte/hoerspiele",
        }]
        self.assertEqual(validate_catalogue([record]), [])


if __name__ == "__main__":
    unittest.main()
