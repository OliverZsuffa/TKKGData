from __future__ import annotations

import unittest

from bs4 import BeautifulSoup

from scraper.sources.archive import discover_archive_episodes, parse_archive_episode, _resolve_index_link
from scraper.sources.official import (
    SUPPLEMENTAL_DETAIL_URLS,
    discover_official_episodes,
    parse_official_detail_page,
    parse_official_page,
)
from scraper.sources.tumblr import parse_tumblr_episode


class FakeClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def get_html(self, url: str):
        if url not in self.pages:
            raise AssertionError(f"Unexpected URL requested by parser test: {url}")
        return BeautifulSoup(self.pages[url], "html.parser")


def official_product(number: int, title: str, synopsis: str, image_number: int | None = None, listening_url: str | None = None) -> str:
    image_number = number if image_number is None else image_number
    panel_id = f"detail{number}"
    listening_anchor = f'<a href="{listening_url}">Jetzt anhören</a>' if listening_url else ""
    return f'''
      <div class="row mb-10">
        <div class="col-12 col-md-6 col-lg-4 mb-16">
          <div class="teaser">
            <img src="/cover-{image_number}.jpg" alt="TKKG Hörspiel-Folge {image_number}: {title}">
            <div class="teaser-body"><h3>{title}</h3></div>
            <a class="icon-link modal-trigger" data-modal="#{panel_id}" href="/produkte/details/test">Details</a>
          </div>
        </div>
        <div id="{panel_id}" class="col-12 order-md-last collapse fade d-none">
          <div class="d-flex flex-column">
            <div class="order-0"><h3 class="h1">{title}</h3><h4>TKKG Hörspiel-Folge {number}</h4></div>
            <div class="order-2">
              <h5>Inhalt</h5><p>{synopsis}</p>
              <h5>Sprecher</h5><p>Tim - Sascha Draeger<br>Karl - Tobias Diakow</p>
              <h5>Details</h5><p>Produktion und Regie: Heikedine Körting<br>Redaktion: Petra Delmar</p>
            </div>
          </div>
          {listening_anchor}
        </div>
      </div>
    '''


def official_detail(number: int, title: str, synopsis: str, date: str) -> str:
    return f'''
      <h1>{title}</h1>
      <h2>TKKG Hörspiel-Folge {number}</h2>
      <img src="/cover-{number}.jpg" alt="TKKG Hörspiel-Folge {number}: {title}">
      <p>Veröffentlichkeitsdatum: {date}</p>
      <div class="col-md-6">
        <h3>Inhalt</h3><p>{synopsis}</p>
        <h3>Sprecher</h3><p>Tim - Sascha Draeger<br>Karl - Tobias Diakow</p>
        <h3>Details</h3><p>Produktion und Regie: Heikedine Körting<br>Redaktion: Petra Delmar</p>
      </div>
    '''


class SourceParserTests(unittest.TestCase):
    def test_archive_index_discovers_episode_link(self):
        client = FakeClient({
            "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie.html": '''
              <a href="/de/hoeren/hoerspiele/serie/folge-001/inhalt.html">Folge 001: Die Jagd nach den Millionendieben</a>
            '''
        })
        records = discover_archive_episodes(client)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["number"], 1)
        self.assertEqual(records[0]["title"], "Die Jagd nach den Millionendieben")
        self.assertEqual(records[0]["source_url"], "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html")

    def test_archive_resolves_real_world_href_forms_without_duplicate_path(self):
        expected = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html"
        hrefs = [
            "/de/hoeren/hoerspiele/serie/folge-001/inhalt.html",
            "de/hoeren/hoerspiele/serie/folge-001/inhalt.html",
            "serie/folge-001/inhalt.html",
            expected,
            "https://www.tkkg-site.de/de/hoeren/hoerspiele/de/hoeren/hoerspiele/serie/folge-001/inhalt.html",
        ]
        for href in hrefs:
            with self.subTest(href=href):
                self.assertEqual(_resolve_index_link(href), expected)

    def test_archive_keeps_audio_subdomain_links_unchanged(self):
        href = "https://audio.tkkg-site.de/post/175481640949/folge207"
        self.assertEqual(_resolve_index_link(href), href)

    def test_archive_cover_prefers_episode_original_for_001(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 001: Die Jagd nach den Millionendieben</h1>
          <img src="/uploads/pics/001_thumbnail.jpg" alt="Folge 001 thumbnail">
          <img src="/uploads/pics/001_01.jpg" alt="Cover Folge 001">
        '''})
        record = parse_archive_episode(client, {"number": 1, "title": "Die Jagd nach den Millionendieben", "source_url": url, "source_name": "TKKG-Site archive"})
        self.assertEqual(record["cover_url"], "https://www.tkkg-site.de/uploads/pics/001_01.jpg")

    def test_archive_cover_supports_episode_002_filename_without_suffix(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-002/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 002: Das Geheimnis der chinesischen Vase</h1>
          <img src="/uploads/pics/002.jpg" alt="Cover Folge 002">
        '''})
        record = parse_archive_episode(client, {"number": 2, "title": "Das Geheimnis der chinesischen Vase", "source_url": url, "source_name": "TKKG-Site archive"})
        self.assertEqual(record["cover_url"], "https://www.tkkg-site.de/uploads/pics/002.jpg")

    def test_archive_cover_finds_later_episode_in_lazy_loaded_image(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-106/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 106: Der Mann ohne Kopf</h1>
          <img src="/uploads/pics/site-logo.jpg" alt="TKKG">
          <img data-src="/uploads/pics/106_02.jpg" alt="Cover Folge 106">
        '''})
        record = parse_archive_episode(client, {"number": 106, "title": "Der Mann ohne Kopf", "source_url": url, "source_name": "TKKG-Site archive"})
        self.assertEqual(record["cover_url"], "https://www.tkkg-site.de/uploads/pics/106_02.jpg")

    def test_archive_detail_extracts_synopsis_tracks_and_release(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html"
        client = FakeClient({
            url: '''
              <h1>Folge 001: Die Jagd nach den Millionendieben</h1>
              <img alt="Folge 001: Die Jagd nach den Millionendieben" src="/cover.jpg">
              <p>Medium:</p><p>LP / MC / CD</p>
              <p>Label:</p><p>EUROPA</p>
              <p>Erscheinungstermin:</p><p>1981 (LP / MC) / 12. Mai 2003 (CD)</p>
              <p>EAN:</p><p>743219895943 (MC)</p>
              <h3>Klappentext</h3><p>Ein spannender Fall.</p>
              <h3>Trackpunkte</h3><ol><li>Erster Track</li><li>Zweiter Track</li></ol>
              <h3>Sprecher</h3><dl><dt>Tim</dt><dd><a>Sascha Draeger</a></dd></dl>
              <h3>Produktion</h3><p>Produktion und Regie: Heikedine Körting</p>
            '''
        })
        discovered = {"number": 1, "title": "Die Jagd nach den Millionendieben", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_archive_episode(client, discovered)
        self.assertEqual(record["synopsis"], "Ein spannender Fall.")
        self.assertEqual(record["release_year"], 1981)
        self.assertEqual(len(record["tracks"]), 2)
        physical = record["physical_releases"][0]
        self.assertEqual(physical["medium"], "LP / MC / CD")
        self.assertEqual(physical["label"], "EUROPA")
        self.assertEqual(physical["release_date"], "1981 (LP / MC) / 12. Mai 2003 (CD)")
        self.assertEqual(physical["ean"], "743219895943 (MC)")

    def test_archive_release_metadata_reads_parallel_label_and_value_columns(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 001: Die Jagd nach den Millionendieben</h1>
          <div class="release-row">
            <div class="release-labels">
              <p>Medium:</p><p>Label:</p><p>Erscheinungstermin:</p><p>EAN:</p>
            </div>
            <div class="release-values">
              <p>LP / MC / CD</p><p>EUROPA</p>
              <p>1981 (LP / MC) / 12. Mai 2003 (CD)</p>
              <p>743219895943 (MC) / 743219895929 (CD)</p>
            </div>
          </div>
        '''})
        discovered = {"number": 1, "title": "Die Jagd nach den Millionendieben", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_archive_episode(client, discovered)
        physical = record["physical_releases"][0]
        self.assertEqual(physical["medium"], "LP / MC / CD")
        self.assertEqual(physical["label"], "EUROPA")
        self.assertEqual(physical["release_date"], "1981 (LP / MC) / 12. Mai 2003 (CD)")
        self.assertEqual(physical["ean"], "743219895943 (MC) / 743219895929 (CD)")
        self.assertEqual(record["release_year"], 1981)

    def test_archive_release_metadata_omits_missing_fields_without_shifting_values(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-003/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 003: Das leere Grab im Moor</h1>
          <div class="release-row">
            <div class="release-labels"><p>Medium:</p><p>Label:</p><p>EAN:</p></div>
            <div class="release-values"><p>MC</p><p>EUROPA</p><p>743219896032</p></div>
          </div>
        '''})
        discovered = {"number": 3, "title": "Das leere Grab im Moor", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_archive_episode(client, discovered)
        physical = record["physical_releases"][0]
        self.assertEqual(physical["medium"], "MC")
        self.assertEqual(physical["label"], "EUROPA")
        self.assertEqual(physical["ean"], "743219896032")
        self.assertNotIn("release_date", physical)
        self.assertIsNone(record["release_year"])

    def test_archive_speaker_parser_ignores_footer_and_navigation_links(self):
        url = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-206/inhalt.html"
        client = FakeClient({url: '''
          <h1>Folge 206: Achtung, UFO-Kult!</h1>
          <h3>Sprecher</h3>
          <dl>
            <dt>Tim</dt><dd><a href="/sprecher/sascha-draeger">Sascha Draeger</a></dd>
            <dt>Karl</dt><dd><a href="/sprecher/tobias-diakow">Tobias Diakow</a></dd>
            <dt>Kommissar Schalavsky</dt><dd><a href="/sprecher/stephan-schad">Stephan Schad</a></dd>
          </dl>
          <footer>
            <nav>
              <a href="/serie">Kommissar Krause · Hörspiele</a>
              <a href="/serie">Kommissar Krause · Serie</a>
              <a href="/einzeltitel">Einzeltitel</a>
              <a href="/boxen">TKKG-Boxen</a>
              <a href="/musik">Musik</a>
              <a href="/archiv">TKKG-Site.de-Archiv</a>
              <a href="/blog">Blog</a><a href="/forum">Forum</a>
              <a href="#top">nach oben</a><a href="/">Startseite</a>
              <a href="/kontakt">Kontakt</a><a href="/datenschutz">Datenschutz</a>
              <a href="/impressum">Impressum</a>
            </nav>
          </footer>
          <h3>Produktion</h3><p>Regie: Heikedine Körting</p>
        '''})
        discovered = {"number": 206, "title": "Achtung, UFO-Kult!", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_archive_episode(client, discovered)
        self.assertEqual(record["cast"], [
            {"name": "Sascha Draeger", "character": "Tim"},
            {"name": "Tobias Diakow", "character": "Karl"},
            {"name": "Stephan Schad", "character": "Kommissar Schalavsky"},
        ])
        self.assertFalse(any("Kommissar Krause" in item["name"] for item in record["cast"]))
        self.assertFalse(any(item["name"] in {"Einzeltitel", "TKKG-Boxen", "Musik", "TKKG-Site.de-Archiv", "Blog", "Forum", "nach oben", "Startseite", "Kontakt", "Datenschutz", "Impressum"} for item in record["cast"]))

    def test_official_page_extracts_details_from_linked_teaser_and_collapse_panel(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        html = official_product(243, "Die Fährte des Hehlers", "Ein Fall mit einem Hehler.", listening_url="https://tkkg.lnk.to/-243AW")
        client = FakeClient({url: html})
        records = parse_official_page(client, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["number"], 243)
        self.assertEqual(records[0]["title"], "Die Fährte des Hehlers")
        self.assertEqual(records[0]["synopsis"], "Ein Fall mit einem Hehler.")
        self.assertEqual(records[0]["cast"], [
            {"name": "Sascha Draeger", "character": "Tim"},
            {"name": "Tobias Diakow", "character": "Karl"},
        ])
        self.assertEqual(records[0]["credits"], [
            {"role": "Produktion und Regie", "name": "Heikedine Körting"},
            {"role": "Redaktion", "name": "Petra Delmar"},
        ])
        self.assertTrue(records[0]["cover_url"].endswith("/cover-243.jpg"))
        self.assertEqual(records[0]["listening_links"], [{
            "service": "official",
            "label": "Official listening page",
            "url": "https://tkkg.lnk.to/-243AW",
            "link_type": "official_hub",
            "source_url": url,
        }])

    def test_official_page_excludes_movie_tie_in_numbered_500(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        title = "Jede Legende hat Ihren Anfang (Hörspiel zum Kinofilm)"
        client = FakeClient({url: official_product(500, title, "Hörspiel zum Kinofilm.")})
        diagnostics = []
        records = parse_official_page(client, 0, diagnostics)
        self.assertEqual(records, [])
        self.assertEqual(diagnostics[0]["number"], 500)
        self.assertEqual(diagnostics[0]["title"], title)
        self.assertIn("excluded special product", diagnostics[0]["reason"])

    def test_official_page_excludes_special_releases_mislabeled_with_series_numbers(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        special_products = [
            (208, "Adventskalender: Ein fast perfektes Weihnachtsmenü"),
            (209, "Das Geheimnis um TKKG (Neuaufnahme)"),
            (221, "Schreckliche Weihnacht überall (Adventskalender)"),
            (239, "Die Weihnachtsgeiseln"),
        ]
        for number, title in special_products:
            with self.subTest(number=number, title=title):
                client = FakeClient({url: official_product(number, title, "Special release.")})
                diagnostics = []
                records = parse_official_page(client, 0, diagnostics)
                self.assertEqual(records, [])
                self.assertEqual(diagnostics[0]["number"], number)
                self.assertIn("excluded special product", diagnostics[0]["reason"])

    def test_official_page_rejects_number_heading_outside_product_detail_panel(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        client = FakeClient({url: official_product(243, "Die Fährte des Hehlers", "Ein Fall.") + "<h4>TKKG Hörspiel-Folge 500</h4>"})
        diagnostics = []
        records = parse_official_page(client, 0, diagnostics)
        self.assertEqual([record["number"] for record in records], [243])
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["number"], 500)
        self.assertIn("not inside a uniquely identified collapsed detail panel", diagnostics[0]["reason"])

    def test_official_page_rejects_mismatched_cover_number(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        client = FakeClient({url: official_product(500, "Unrelated product", "Not the episode.", image_number=243)})
        diagnostics = []
        records = parse_official_page(client, 0, diagnostics)
        self.assertEqual(records, [])
        self.assertEqual(diagnostics[0]["number"], 500)
        self.assertIn("conflicts with cover image number 243", diagnostics[0]["reason"])

    def test_official_detail_page_extracts_missing_episode_metadata(self):
        number = 222
        url = SUPPLEMENTAL_DETAIL_URLS[number]
        client = FakeClient({url: official_detail(number, "Roter Drache 222", "Ein spannender Fall.", "15.04.2022")})
        record = parse_official_detail_page(client, number, url)
        self.assertEqual(record["number"], 222)
        self.assertEqual(record["title"], "Roter Drache 222")
        self.assertEqual(record["synopsis"], "Ein spannender Fall.")
        self.assertEqual(record["release_date"], "2022-04-15")
        self.assertEqual(record["release_year"], 2022)
        self.assertEqual(record["cast"][0], {"name": "Sascha Draeger", "character": "Tim"})
        self.assertTrue(record["cover_url"].endswith("/cover-222.jpg"))
        self.assertEqual(record["sources"][0]["url"], url)

    def test_official_listing_uses_details_copyright_year_without_fabricating_date(self):
        url = "https://www.tkkg.de/produkte/hoerspiele"
        html = official_product(224, "Bilderdiebe haben kein Gesicht", "Ein Fall.")
        html = html.replace(
            "Redaktion: Petra Delmar</p>",
            "Redaktion: Petra Delmar<br>© 2022 - Eine Produktion der Sony Music Entertainment Germany GmbH</p>",
        )
        record = parse_official_page(FakeClient({url: html}), 0)[0]
        self.assertEqual(record["release_year"], 2022)
        self.assertIsNone(record["release_date"])

    def test_official_detail_copyright_year_is_fallback_but_explicit_date_wins(self):
        number = 222
        url = SUPPLEMENTAL_DETAIL_URLS[number]
        html = official_detail(number, "Roter Drache 222", "Ein spannender Fall.", "15.04.2022")
        html = html.replace(
            "Redaktion: Petra Delmar</p>",
            "Redaktion: Petra Delmar<br>© 2020 - Eine Produktion der Sony Music Entertainment Germany GmbH</p>",
        )
        record = parse_official_detail_page(FakeClient({url: html}), number, url)
        self.assertEqual(record["release_date"], "2022-04-15")
        self.assertEqual(record["release_year"], 2022)

        no_date_html = html.replace("<p>Veröffentlichkeitsdatum: 15.04.2022</p>", "")
        fallback = parse_official_detail_page(FakeClient({url: no_date_html}), number, url)
        self.assertIsNone(fallback["release_date"])
        self.assertEqual(fallback["release_year"], 2020)

    def test_official_discovery_uses_verified_detail_fallbacks_for_listing_gaps(self):
        base = "https://www.tkkg.de/produkte/hoerspiele"
        pages = {
            base: official_product(243, "Die Fährte des Hehlers", "Ein Fall."),
            f"{base}?page=1": official_product(243, "Die Fährte des Hehlers", "Ein Fall."),
            f"{base}?page=2": "<p>No episode headings</p>",
            f"{base}?page=3": "<p>No episode headings</p>",
        }
        for number, url in SUPPLEMENTAL_DETAIL_URLS.items():
            pages[url] = official_detail(number, {222: "Roter Drache 222", 223: "Betrüger Super Sauber", 234: "Im Auftrag des Bösen"}[number], "Ein Fall.", "15.04.2022")
        records = discover_official_episodes(FakeClient(pages), max_pages=10)
        by_number = {record["number"]: record for record in records}
        self.assertTrue({222, 223, 234}.issubset(by_number))
        self.assertEqual(by_number[222]["sources"][0]["url"], SUPPLEMENTAL_DETAIL_URLS[222])
        self.assertEqual(by_number[223]["sources"][0]["url"], SUPPLEMENTAL_DETAIL_URLS[223])
        self.assertEqual(by_number[234]["sources"][0]["url"], SUPPLEMENTAL_DETAIL_URLS[234])

    def test_tumblr_fallback_strips_archive_catalogue_prefix(self):
        url = "https://audio.tkkg-site.de/post/test/folge207"
        client = FakeClient({
            url: '''
              <h2>TKKG zum Hören — Doppelte Entführung</h2>
              <p>Ein Internetstar wurde entführt.</p>
            '''
        })
        discovered = {"number": 207, "title": "TKKG zum Hören — Doppelte Entführung", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_tumblr_episode(client, discovered)
        self.assertEqual(record["title"], "Doppelte Entführung")

    def test_tumblr_post_extracts_release_and_tracks(self):
        url = "https://audio.tkkg-site.de/post/test/folge207"
        client = FakeClient({
            url: '''
              <h2>Doppelte Entführung (Folge 207)</h2>
              <p>Ein Internetstar wurde entführt.</p>
              <p>EAN: 190758362724</p>
              <p>Veröffentlichungsdatum: 14. September 2018</p>
              <h2>Sprecher</h2><ul><li>Tim - Sascha Draeger</li></ul>
              <h2>CD-Tracks</h2><ol><li>Entführung auf Band</li></ol>
            '''
        })
        discovered = {"number": 207, "title": "Doppelte Entführung", "source_url": url, "source_name": "TKKG-Site archive"}
        record = parse_tumblr_episode(client, discovered)
        self.assertEqual(record["title"], "Doppelte Entführung")
        self.assertEqual(record["release_year"], 2018)
        self.assertEqual(record["physical_releases"][0]["ean"], "190758362724")
        self.assertEqual(record["tracks"][0]["title"], "Entführung auf Band")


if __name__ == "__main__":
    unittest.main()
