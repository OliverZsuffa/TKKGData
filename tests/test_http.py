from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scraper.http import SourceAccessError, SourceClient


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.text = content.decode("iso-8859-1")
        self.status_code = 200
        self.headers = {"Content-Type": "text/html; charset=ISO-8859-1"}

    def raise_for_status(self):
        return None


class SourceClientTests(unittest.TestCase):
    def test_robots_denial_is_cached_and_fails_closed(self):
        class DeniedResponse:
            status_code = 403
            text = "Forbidden"

        client = SourceClient(delay_seconds=0)
        denied = DeniedResponse()
        with patch.object(client.session, "get", return_value=denied) as get:
            for url in (
                "https://audio.tkkg-site.de/post/episode-207",
                "https://audio.tkkg-site.de/post/episode-208",
            ):
                with self.assertRaisesRegex(SourceAccessError, "robots.txt.*HTTP 403"):
                    client.get_html(url)
        self.assertEqual(get.call_count, 1)

    def test_get_html_decodes_declared_utf8_from_response_bytes_and_caches_bytes(self):
        url = "https://example.test/episode"
        payload = '<meta charset="utf-8"><p>Mörderischer Stammbaum</p>'.encode("utf-8")
        response = FakeResponse(payload)
        client = SourceClient(delay_seconds=0)
        client._robots["https://example.test"] = None

        with patch.object(client.session, "get", return_value=response) as get:
            first = client.get_html(url)
            second = client.get_html(url)

        self.assertIn("Mörderischer Stammbaum", first.get_text())
        self.assertNotIn("MÃ¶rderischer Stammbaum", first.get_text())
        self.assertIn("Mörderischer Stammbaum", second.get_text())
        self.assertEqual(get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
