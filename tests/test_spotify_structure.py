import unittest
from scraper.spotify_structure import classify_track, validate_episode_parts

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

    def test_two_disc_repeated_numbers(self):
        tracks = [{"name":f"Teil {i:02}","disc_number":d,"track_number":i} for d in (1,2) for i in range(1,3)]
        result = validate_episode_parts(tracks, "two_disc_duplicated_numbering")
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["parts"]),4)

if __name__ == "__main__":
    unittest.main()
