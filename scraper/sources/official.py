from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from scraper.http import SourceClient


BASE_URL = "https://www.tkkg.de/produkte/hoerspiele"
EPISODE_HEADING = re.compile(r"TKKG\s+Hörspiel-Folge\s+(\d+)", re.IGNORECASE)
HEADING_TAGS = {"h3", "h4", "h5", "h6"}

# The listing omits these three main-series episodes, although their official
# product detail pages remain publicly available. Keep these verified fallbacks
# explicit rather than synthesizing slugs or relaxing catalogue completeness.
SUPPLEMENTAL_DETAIL_URLS = {
    222: "https://www.tkkg.de/produkte/details/roter-drache-222",
    223: "https://www.tkkg.de/produkte/details/betruger-super-sauber",
    234: "https://www.tkkg.de/produkte/details/im-auftrag-des-bosen",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _section_lines(panel: Tag | BeautifulSoup, label: str) -> list[str]:
    headings = panel.find_all(list(HEADING_TAGS))
    target = next((h for h in headings if _clean(h.get_text(" ", strip=True)).casefold() == label.casefold()), None)
    if target is None:
        return []
    lines: list[str] = []
    for sibling in target.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in HEADING_TAGS:
            break
        if isinstance(sibling, Tag):
            value = sibling.get_text("\n", strip=True)
            lines.extend(_clean(line) for line in value.splitlines() if _clean(line))
        elif str(sibling).strip():
            lines.append(_clean(str(sibling)))
    return lines


def _section(panel: Tag | BeautifulSoup, label: str) -> str | None:
    result = _clean(" ".join(_section_lines(panel, label)))
    return result or None


def _find_detail_panel(heading: Tag) -> Tag | None:
    """Find the collapsed detail panel containing this episode heading."""
    for parent in heading.parents:
        if not isinstance(parent, Tag):
            continue
        classes = parent.get("class", [])
        if (
            parent.name == "div"
            and parent.get("id")
            and "collapse" in classes
            and len(parent.find_all("h4")) == 1
        ):
            return parent
    return None


def _find_product_teaser(panel: Tag) -> Tag | None:
    """Pair the detail panel with its adjacent teaser through the site's data-modal id."""
    panel_id = panel.get("id")
    teaser = panel.find_previous_sibling("div")
    if not panel_id or not isinstance(teaser, Tag):
        return None
    trigger = teaser.find("a", attrs={"data-modal": f"#{panel_id}"})
    if trigger is None or teaser.find("img") is None or teaser.find(["h2", "h3"]) is None:
        return None
    return teaser


def _base_record(number: int, title: str, url: str, synopsis: str | None, cover_url: str | None,
                 release_date: str | None, release_year: int | None, cast: list[dict], credits: list[dict]) -> dict:
    return {
        "number": number,
        "title": title,
        "synopsis": synopsis,
        "cover_url": cover_url,
        "release_date": release_date,
        "release_year": release_year,
        "physical_releases": [],
        "tracks": [],
        "cast": cast,
        "credits": credits,
        "ratings": [],
        "listening_links": [],
        "sources": [{"name": "Official TKKG catalogue", "url": url}],
    }


def _copyright_year(panel: Tag | BeautifulSoup) -> int | None:
    """Return a year explicitly stated in the episode's Details copyright line."""
    for line in _section_lines(panel, "Details"):
        if re.search(r"©\s*", line):
            match = re.search(r"©\s*((?:19|20)\d{2})\b", line)
            if match:
                return int(match.group(1))
    return None


def _parse_cast(panel: Tag | BeautifulSoup) -> list[dict]:
    cast = []
    for line in _section_lines(panel, "Sprecher"):
        if " - " in line:
            character, name = line.split(" - ", 1)
            cast.append({"name": _clean(name), "character": _clean(character)})
    return cast


def _parse_credits(panel: Tag | BeautifulSoup) -> list[dict]:
    credits = []
    for line in _section_lines(panel, "Details"):
        if ":" in line:
            role, name = line.split(":", 1)
            credits.append({"role": _clean(role), "name": _clean(name)})
    return credits



def _official_listening_link(panel: Tag, source_url: str) -> list[dict]:
    """Extract the episode-specific Linkfire destination from this card only."""
    candidates = list(panel.find_all("a"))
    for sibling in panel.next_siblings:
        if not isinstance(sibling, Tag):
            continue
        # The next product teaser marks the end of this episode's card.
        if sibling.name == "div" and sibling.find("img") and sibling.find(["h2", "h3"]):
            break
        candidates.extend([sibling] if sibling.name == "a" else sibling.find_all("a"))

    for anchor in candidates:
        label = _clean(anchor.get_text(" ", strip=True)).casefold()
        href = anchor.get("href")
        if label != "jetzt anhören" or not isinstance(href, str):
            continue
        destination = urljoin(source_url, href)
        parsed = urlparse(destination)
        if parsed.scheme == "https" and parsed.hostname == "tkkg.lnk.to" and parsed.path not in ("", "/alle-hoerspiele"):
            # DNS hostnames are case-insensitive; store the canonical lowercase
            # hostname so schema validation and downstream comparisons agree.
            destination = parsed._replace(netloc=parsed.netloc.lower()).geturl()
            return [{
                "service": "official",
                "label": "Official listening page",
                "url": destination,
                "link_type": "official_hub",
                "source_url": source_url,
            }]
    return []

def parse_official_page(client: SourceClient, page_number: int, diagnostics: list[dict] | None = None) -> list[dict]:
    url = BASE_URL if page_number == 0 else f"{BASE_URL}?page={page_number}"
    soup = client.get_html(url)
    records: list[dict] = []
    for episode_heading in soup.find_all(["h4", "h5", "h6"]):
        match = EPISODE_HEADING.search(_clean(episode_heading.get_text(" ", strip=True)))
        if not match:
            continue
        number = int(match.group(1))
        panel = _find_detail_panel(episode_heading)
        if panel is None:
            if diagnostics is not None:
                diagnostics.append({
                    "number": number,
                    "title": None,
                    "source_url": url,
                    "reason": "episode-number heading is not inside a uniquely identified collapsed detail panel",
                })
            continue

        teaser = _find_product_teaser(panel)
        if teaser is None:
            if diagnostics is not None:
                diagnostics.append({
                    "number": number,
                    "title": None,
                    "source_url": url,
                    "detail_panel_id": panel.get("id"),
                    "reason": "detail panel has no adjacent product teaser linked by its data-modal id",
                })
            continue

        title_heading = teaser.find(["h2", "h3"])
        title = _clean(title_heading.get_text(" ", strip=True)) if title_heading else ""
        image = teaser.find("img")
        alt = _clean(image.get("alt", "")) if image else ""
        alt_match = EPISODE_HEADING.search(alt)
        if alt_match and int(alt_match.group(1)) != number:
            if diagnostics is not None:
                diagnostics.append({
                    "number": number,
                    "title": title or None,
                    "source_url": url,
                    "detail_panel_id": panel.get("id"),
                    "image_alt": alt,
                    "reason": f"episode heading number {number} conflicts with cover image number {int(alt_match.group(1))}",
                })
            continue

        if not title:
            title_match = re.search(r"Folge\s+\d+\s*:\s*(.+)$", alt, re.IGNORECASE)
            title = _clean(title_match.group(1)) if title_match else ""
        excluded_terms = ("live-album", "live album", "hörspiel-box", "krimi-box", "hörspiel zum kinofilm", "adventskalender", "neuaufnahme", "die weihnachtsgeiseln")
        if not title or any(term in title.casefold() for term in excluded_terms):
            if diagnostics is not None:
                diagnostics.append({
                    "number": number,
                    "title": title or None,
                    "source_url": url,
                    "detail_panel_id": panel.get("id"),
                    "reason": "missing product title or excluded special product",
                })
            continue

        image_url = None
        if image:
            image_src = image.get("src") or image.get("data-src") or image.get("data-lazy-src")
            if image_src:
                image_url = urljoin(url, image_src)

        record = _base_record(
            number=number,
            title=title,
            url=url,
            synopsis=_section(panel, "Inhalt"),
            cover_url=image_url,
            release_date=None,
            release_year=_copyright_year(panel),
            cast=_parse_cast(panel),
            credits=_parse_credits(panel),
        )
        record["listening_links"] = _official_listening_link(panel, url)
        records.append(record)
    return records


def parse_official_detail_page(client: SourceClient, number: int, url: str) -> dict:
    """Parse a verified official product page used when the listing omits an episode."""
    soup = client.get_html(url)
    heading = next(
        (h for h in soup.find_all(["h2", "h3", "h4", "h5", "h6"])
         if EPISODE_HEADING.search(_clean(h.get_text(" ", strip=True)))),
        None,
    )
    match = EPISODE_HEADING.search(_clean(heading.get_text(" ", strip=True))) if heading else None
    if match is None or int(match.group(1)) != number:
        found = int(match.group(1)) if match else None
        raise ValueError(f"Expected official episode {number} at {url}, found {found}.")

    title_heading = soup.find("h1")
    title = _clean(title_heading.get_text(" ", strip=True)) if title_heading else ""
    if not title:
        raise ValueError(f"Official detail page has no title for episode {number}: {url}")

    image = next(
        (img for img in soup.find_all("img", alt=True)
         if (image_match := EPISODE_HEADING.search(_clean(img.get("alt", ""))))
         and int(image_match.group(1)) == number),
        None,
    )
    image_url = None
    if image:
        image_src = image.get("src") or image.get("data-src") or image.get("data-lazy-src")
        if image_src:
            image_url = urljoin(url, image_src)

    body_text = soup.get_text(" ", strip=True)
    date_match = re.search(r"Veröffentlich(?:ungs|keits)datum:\s*(\d{2}\.\d{2}\.\d{4})", body_text, re.IGNORECASE)
    release_date = None
    release_year = None
    if date_match:
        parsed_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        release_date = parsed_date.isoformat()
        release_year = parsed_date.year
    else:
        release_year = _copyright_year(soup)

    record = _base_record(
        number=number,
        title=title,
        url=url,
        synopsis=_section(soup, "Inhalt"),
        cover_url=image_url,
        release_date=release_date,
        release_year=release_year,
        cast=_parse_cast(soup),
        credits=_parse_credits(soup),
    )
    for anchor in soup.find_all("a"):
        if _clean(anchor.get_text(" ", strip=True)).casefold() != "jetzt anhören":
            continue
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        destination = urljoin(url, href)
        parsed = urlparse(destination)
        if parsed.scheme == "https" and parsed.hostname == "tkkg.lnk.to" and parsed.path not in ("", "/alle-hoerspiele"):
            record["listening_links"] = [{
                "service": "official",
                "label": "Official listening page",
                "url": destination,
                "link_type": "official_hub",
                "source_url": url,
            }]
            break
    return record


def discover_official_episodes(client: SourceClient, max_pages: int = 30, diagnostics: list[dict] | None = None) -> list[dict]:
    records: dict[tuple[int, str], dict] = {}
    empty_pages = 0
    for page in range(max_pages):
        page_records = parse_official_page(client, page, diagnostics)
        if not page_records:
            empty_pages += 1
            if empty_pages >= 2:
                break
            continue
        empty_pages = 0
        for record in page_records:
            records[(record["number"], record["title"])] = record

    # A few regular episodes are absent from the listing grid but have verified
    # first-party product pages. Fetch these only when the listing has no record
    # for that episode; keep the completeness guard active if a fallback fails.
    existing_numbers = {record["number"] for record in records.values()}
    for number, url in SUPPLEMENTAL_DETAIL_URLS.items():
        if number not in existing_numbers:
            record = parse_official_detail_page(client, number, url)
            records[(record["number"], record["title"])] = record
    return list(records.values())
