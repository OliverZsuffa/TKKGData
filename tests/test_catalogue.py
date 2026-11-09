from __future__ import annotations

import unittest

from scraper.merge import merge_records
from scraper.validate import find_number_gaps, listening_link_coverage, validate_catalogue


def episode(number: int, title: str, **extra) -> dict:
    value = {
        "number": number,
        "title": title,
        "series": "TKKG",
        "synopsis": None,
        "cover_url": None,
        "release_date": None,
        "release_year": None,
        "physical_releases": [],
        "tracks": [],
        "cast": [],
        "credits": [],
        "ratings": [],
        "listening_links": [],
        "sources": [{"name": "test", "url": "https://example.com/episode", "retrieved_at": "2026-10-18T00:00:00+00:00"}],
        "last_checked": "2026-10-18T00:00:00+00:00",
    }
    value.update(extra)
    return value


class CatalogueTests(unittest.TestCase):
    def test_valid_episode_passes_schema(self):
        self.assertEqual(validate_catalogue([episode(1, "Test Folge")]), [])

    def test_invalid_listening_destination_is_rejected(self):
        malformed = episode(1, "Test Folge", listening_links=[{
            "service": "official",
            "label": "Official listening page",
            "url": "https://example.com/episode",
            "link_type": "official_hub",
            "source_url": "https://www.tkkg.de/produkte/hoerspiele",
        }])
        errors = validate_catalogue([malformed])
        self.assertTrue(any("does not match" in error for error in errors))

    def test_duplicate_numbers_are_rejected(self):
        errors = validate_catalogue([episode(1, "A"), episode(1, "B")])
        self.assertTrue(any("duplicate episode number 1" in error for error in errors))

    def test_missing_title_is_rejected(self):
        errors = validate_catalogue([episode(1, "")])
        self.assertTrue(errors)

    def test_gaps_are_reported(self):
        self.assertEqual(find_number_gaps([episode(1, "A"), episode(3, "C")]), [2])

    def test_missing_first_episode_is_reported(self):
        self.assertEqual(find_number_gaps([episode(2, "B"), episode(3, "C")]), [1])

    def test_merge_preserves_metadata_and_sources(self):
        base = episode(1, "A")
        enrichment = episode(
            1,
            "A",
            synopsis="A description",
            cast=[{"name": "Actor", "character": "Role"}],
            sources=[{"name": "second source", "url": "https://example.org/episode", "retrieved_at": "2026-10-18T00:00:00+00:00"}],
        )
        merged, conflicts = merge_records([base, enrichment])
        self.assertEqual(conflicts, [])
        self.assertEqual(merged[0]["synopsis"], "A description")
        self.assertEqual(len(merged[0]["cast"]), 1)
        self.assertEqual(len(merged[0]["sources"]), 2)

    def test_release_metadata_field_labels_are_rejected(self):
        malformed = episode(1, "Test Folge", physical_releases=[{
            "medium": "Label:",
            "label": "Erscheinungstermin:",
            "ean": "LP / MC / CD",
            "release_date": "EAN:",
            "source_url": "https://example.com/episode",
        }])
        errors = validate_catalogue([malformed])
        self.assertTrue(any("medium contains a field label" in error for error in errors))
        self.assertTrue(any("label contains a field label" in error for error in errors))
        self.assertTrue(any("release_date contains a field label" in error for error in errors))
        self.assertTrue(any("EAN contains no plausible" in error for error in errors))

    def test_release_metadata_accepts_realistic_archive_values(self):
        valid = episode(1, "Test Folge", physical_releases=[{
            "medium": "LP / MC / CD",
            "label": "EUROPA",
            "ean": "743219895943 (MC) / 743219895929 (CD)",
            "release_date": "1981 (LP / MC) / 12. Mai 2003 (CD)",
            "source_url": "https://example.com/episode",
        }], release_year=1981)
        self.assertEqual(validate_catalogue([valid]), [])

    def test_merge_preserves_official_listening_links(self):
        base = episode(1, "A")
        enrichment = episode(1, "A", listening_links=[{
            "service": "official",
            "label": "Official listening page",
            "url": "https://tkkg.lnk.to/-001AW",
            "link_type": "official_hub",
            "source_url": "https://www.tkkg.de/produkte/hoerspiele",
        }])
        merged, conflicts = merge_records([base, enrichment])
        self.assertEqual(conflicts, [])
        self.assertEqual(merged[0]["listening_links"], enrichment["listening_links"])

    def test_listening_link_coverage_reports_hubs_and_missing_episodes(self):
        linked = episode(1, "A", listening_links=[{
            "service": "official",
            "label": "Official listening page",
            "url": "https://tkkg.lnk.to/-001AW",
            "link_type": "official_hub",
            "source_url": "https://www.tkkg.de/produkte/hoerspiele",
        }])
        coverage = listening_link_coverage([linked, episode(2, "B")])
        self.assertEqual(coverage["episode_count"], 2)
        self.assertEqual(coverage["episodes_with_listening_links"], 1)
        self.assertEqual(coverage["episodes_without_listening_links"], [{"number": 2, "title": "B"}])
        self.assertEqual(coverage["links_by_service"], {"official": 1})
        self.assertEqual(coverage["links_by_type"], {"official_hub": 1})
        self.assertEqual(coverage["direct_episode_or_release_link_count"], 0)
        self.assertEqual(coverage["hub_or_fallback_link_count"], 1)
        self.assertEqual(coverage["invalid_links"], [])

    def test_title_conflicts_are_reported(self):
        merged, conflicts = merge_records([episode(1, "A"), episode(1, "Different")])
        self.assertEqual(merged[0]["title"], "A")
        self.assertEqual(len(conflicts), 1)


if __name__ == "__main__":
    unittest.main()
