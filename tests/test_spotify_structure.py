import unittest
from scraper.spotify_structure import classify_track, validate_episode_parts, validate_selected_track_positions

class SpotifyStructureTests(unittest.TestCase):
    def test_extras_and_parts(self):
        self.assertEqual(classify_track({"name":"Inhaltsangabe"})["classification"], "summary")
        self.assertEqual(classify_track({"name":"TKKG Titelsong"})["classification"], "opening_song")
        self.assertEqual(classify_track({"name":"Teil 08"})["part_number"], 8)
        self.assertEqual(classify_track({"name":"Outro"})["classification"], "outro")

    def test_standard_sequence_and_unknown(self):
        result = validate_episode_parts([{"name":"Teil 02"},{"name":"Outro"},{"name":"Teil 01"},{"name":"Mystery track"}])
        self.assertTrue(result["valid"])
        self.assertEqual([t["part_number"] for t in result["parts"]], [1,2])
        self.assertEqual(len(result["extras"]), 1)
        self.assertEqual(len(result["unknown"]), 1)

    def test_gap_rejected(self):
        result = validate_episode_parts([{"name":"Teil 01"},{"name":"Teil 03"}])
        self.assertFalse(result["valid"])

    def test_episode_parts_may_have_extras_between_album_positions(self):
        tracks = [
            {"name": "Teil 01", "disc_number": 1, "track_number": 1},
            {"name": "Inhaltsangabe", "disc_number": 1, "track_number": 2},
            {"name": "Teil 02", "disc_number": 1, "track_number": 3},
            {"name": "Outro", "disc_number": 1, "track_number": 4},
            {"name": "Teil 03", "disc_number": 1, "track_number": 5},
        ]
        self.assertEqual(validate_selected_track_positions(tracks), [])

    def test_selected_part_number_gap_is_rejected(self):
        tracks = [
            {"name": "Teil 01", "track_number": 1},
            {"name": "Teil 03", "track_number": 4},
        ]
        self.assertIn("Episode part numbering", validate_selected_track_positions(tracks)[0])

    def test_unlabelled_noncontiguous_selection_is_rejected(self):
        tracks = [
            {"name": "Episode", "track_number": 1},
            {"name": "Episode continued", "track_number": 3},
        ]
        self.assertIn("not contiguous", validate_selected_track_positions(tracks)[0])

    def test_duplicate_album_positions_are_rejected(self):
        tracks = [
            {"name": "Teil 01", "track_number": 1},
            {"name": "Teil 02", "track_number": 1},
        ]
        self.assertIn("duplicate positions", validate_selected_track_positions(tracks)[0])

    def test_full_release_keeps_summary_intro_parts_outro_and_outsong_in_album_order(self):
        tracks = [
            {"name": "Inhaltsangabe", "disc_number": 1, "track_number": 1},
            {"name": "Intro", "disc_number": 1, "track_number": 2},
            {"name": "Teil 01", "disc_number": 1, "track_number": 3},
            {"name": "Teil 02", "disc_number": 1, "track_number": 4},
            {"name": "Outro", "disc_number": 1, "track_number": 5},
            {"name": "Outsong", "disc_number": 1, "track_number": 6},
        ]
        result = validate_episode_parts(tracks)
        self.assertTrue(result["valid"])
        self.assertEqual(
            [track["name"] for track in result["tracks"]],
            [track["name"] for track in tracks],
        )
        self.assertEqual(len(result["parts"]), 2)
        self.assertEqual([track["track_number"] for track in result["tracks"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(
            [track["classification"] for track in result["tracks"]],
            ["summary", "intro", "episode_part", "episode_part", "outro", "closing_song"],
        )

    def test_shared_title_song_and_episode_extras_are_preserved_without_other_episode_parts(self):
        from scraper.spotify_structure import select_episode_release_tracks

        album = [
            {"name": "TKKG Titelsong", "disc_number": 1, "track_number": 1, "song_id": "song-opening"},
            {"name": "Inhaltsangabe", "disc_number": 1, "track_number": 2, "song_id": "song-summary"},
            {"name": "Teil 01", "disc_number": 1, "track_number": 3, "song_id": "part-1"},
            {"name": "Teil 02", "disc_number": 1, "track_number": 4, "song_id": "part-2"},
            {"name": "Outro", "disc_number": 1, "track_number": 5, "song_id": "song-outro"},
            {"name": "Outsong", "disc_number": 1, "track_number": 6, "song_id": "song-closing"},
            {"name": "225 - Andere Folge Teil 01", "disc_number": 1, "track_number": 7, "song_id": "other-part"},
        ]
        selected_parts = [album[2], album[3]]
        selected = select_episode_release_tracks(album, selected_parts, "shared_title_song")
        self.assertEqual(
            [track["song_id"] for track in selected],
            ["song-opening", "song-summary", "part-1", "part-2", "song-outro", "song-closing"],
        )
        self.assertEqual(validate_selected_track_positions(selected), [])

    def test_explicitly_selected_single_track_compilation_episode_is_kept(self):
        from scraper.spotify_structure import select_episode_release_tracks

        album = [
            {"name": "20 - Das Geheimnis der alten Villa", "track_number": 5, "song_id": "selected"},
            {"name": "21 - Die andere Folge", "track_number": 6, "song_id": "other"},
        ]
        selected = select_episode_release_tracks(album, [album[0]])
        self.assertEqual([track["song_id"] for track in selected], ["selected"])

    def test_unknown_track_inside_episode_sequence_is_rejected(self):
        from scraper.spotify_structure import select_episode_release_tracks

        album = [
            {"name": "Teil 01", "track_number": 1, "song_id": "part-1"},
            {"name": "Unrecognised content", "track_number": 2, "song_id": "unknown"},
            {"name": "Teil 02", "track_number": 3, "song_id": "part-2"},
        ]
        with self.assertRaisesRegex(ValueError, "Unclassified track"):
            select_episode_release_tracks(album, [album[0], album[2]])

    def test_selected_parts_with_shared_intro_and_outro_need_not_be_physically_contiguous(self):
        tracks = [
            {"name": "TKKG Titelsong", "track_number": 1},
            {"name": "Teil 01", "track_number": 4},
            {"name": "Outro", "track_number": 5},
        ]
        self.assertEqual(validate_selected_track_positions(tracks), [])

    def test_duplicate_album_positions_are_rejected(self):
        result = validate_episode_parts([
            {"name": "Teil 01", "disc_number": 1, "track_number": 1},
            {"name": "Teil 02", "disc_number": 1, "track_number": 1},
        ])
        self.assertFalse(result["valid"])
        self.assertIn("duplicate track positions", result["errors"][0])

    def test_two_disc_repeated_numbers(self):
        tracks = [{"name":f"Teil {i:02}","disc_number":d,"track_number":i} for d in (1,2) for i in range(1,3)]
        result = validate_episode_parts(tracks, "two_disc_duplicated_numbering")
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["parts"]),4)

if __name__ == "__main__":
    unittest.main()
