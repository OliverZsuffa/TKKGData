from __future__ import annotations

import unittest

from scraper.migrate_audio_release import migrate_catalogue


class AudioReleaseMigrationTests(unittest.TestCase):
    def legacy_episode(self):
        return {
            "number": 218,
            "title": "Schutzgeld für Dämonen",
            "audio_release": {
                "spotify": {
                    "album_id": "1" * 22,
                    "url": "https://open.spotify.com/album/" + "1" * 22,
                    "title": "218/Schutzgeld für Dämonen",
                    "track_count": 2,
                    "source_query": "reviewed album",
                },
                "youtube_music": {
                    "playlist": None,
                    "track_count": 2,
                    "tracks": [
                        {
                            "track_number": 1,
                            "spotify_title": "218 - Schutzgeld für Dämonen - Teil 01",
                            "spotify_track_id": "2" * 22,
                            "spotify_track_url": "https://open.spotify.com/track/" + "2" * 22,
                            "video_id": "abcdefghijk",
                            "url": "https://music.youtube.com/watch?v=abcdefghijk",
                            "title": "218 - Schutzgeld für Dämonen (Teil 01)",
                            "artists": ["TKKG"],
                            "album": "218/Schutzgeld für Dämonen",
                            "duration_seconds": 120,
                            "match_score": 160,
                            "match_evidence": ["ordered_album_match"],
                        },
                        {
                            "track_number": 2,
                            "spotify_title": "218 - Schutzgeld für Dämonen - Teil 02",
                            "spotify_track_id": "3" * 22,
                            "spotify_track_url": "https://open.spotify.com/track/" + "3" * 22,
                            "video_id": "bcdefghijkl",
                            "url": "https://music.youtube.com/watch?v=bcdefghijkl",
                            "title": "218 - Schutzgeld für Dämonen (Teil 02)",
                            "artists": ["TKKG"],
                            "album": "218/Schutzgeld für Dämonen",
                            "duration_seconds": 118,
                            "match_score": 160,
                            "match_evidence": ["ordered_album_match"],
                        },
                    ],
                },
                "verification": {
                    "status": "verified",
                    "verified_at": "2026-11-24T10:00:00+00:00",
                    "method": "legacy_method",
                    "matched_track_count": 2,
                    "playlist_status": "unavailable",
                    "playlist_error": None,
                },
            },
        }

    def test_migrates_independent_provider_lists_without_legacy_pairing(self):
        migrated, report = migrate_catalogue(
            [self.legacy_episode()], migrated_at="2026-11-24T12:00:00+00:00"
        )
        release = migrated[0]["audio_release"]
        self.assertEqual(release["schema_version"], 2)
        self.assertEqual(release["spotify"]["track_count"], 2)
        self.assertEqual(release["youtube_music"]["track_count"], 2)
        self.assertEqual(release["spotify"]["tracks"][0]["track_id"], "2" * 22)
        self.assertEqual(release["spotify"]["tracks"][1]["title"], "218 - Schutzgeld für Dämonen - Teil 02")
        self.assertEqual(release["youtube_music"]["tracks"][0]["video_id"], "abcdefghijk")
        self.assertEqual(release["youtube_music"]["tracks"][0]["duration_seconds"], 120)
        self.assertNotIn("legacy_pairing", release["youtube_music"]["tracks"][0])
        self.assertNotIn("legacy_pairing", release["youtube_music"]["tracks"][1])
        self.assertEqual(release["verification"]["migration"]["source_verification"]["method"], "legacy_method")
        self.assertEqual(report["migrated_episode_count"], 1)
        self.assertEqual(report["spotify_track_count"], 2)
        self.assertEqual(report["youtube_music_track_count"], 2)

    def test_moves_discovery_hints_and_aliases_into_episode(self):
        migrated, report = migrate_catalogue(
            [self.legacy_episode()],
            {"218": {
                "alternate_titles": ["Schutzgeld fuer Daemonen"],
                "album_id": "1" * 22,
                "profile": "structured_extras",
                "expected_parts": 21,
            }},
            "2026-11-24T12:00:00+00:00",
        )
        episode = migrated[0]
        self.assertEqual(episode["title"], "Schutzgeld für Dämonen")
        self.assertEqual(episode["alternate_titles"], ["Schutzgeld fuer Daemonen"])
        self.assertEqual(episode["audio_discovery"]["spotify"], {
            "preferred_album_id": "1" * 22,
            "release_profile": "structured_extras",
            "expected_story_parts": 21,
        })
        self.assertEqual(report["discovery_hint_episode_count"], 1)
        self.assertEqual(report["alternate_title_count"], 1)

    def test_aborts_if_a_source_track_cannot_be_carried_over(self):
        episode = self.legacy_episode()
        episode["audio_release"]["youtube_music"]["tracks"][0]["video_id"] = None
        with self.assertRaisesRegex(ValueError, "migration aborted"):
            migrate_catalogue([episode])

    def test_rejects_override_for_unknown_episode(self):
        with self.assertRaisesRegex(ValueError, "missing episodes"):
            migrate_catalogue([self.legacy_episode()], {"999": {"profile": "standard"}})

    def test_is_idempotent_for_migrated_data(self):
        migrated, _ = migrate_catalogue(
            [self.legacy_episode()], migrated_at="2026-11-24T12:00:00+00:00"
        )
        second, report = migrate_catalogue(
            migrated, {"218": {"profile": "structured_extras"}}
        )
        self.assertEqual(second[0]["audio_release"], migrated[0]["audio_release"])
        self.assertEqual(report["migrated_episode_count"], 0)


if __name__ == "__main__":
    unittest.main()
