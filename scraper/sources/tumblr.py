from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import Tag

from scraper.http import SourceClient


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_tumblr_episode(client: SourceClient, discovered: dict) -> dict:
    soup = client.get_html(discovered["source_url"])
    heading = soup.find(["h1", "h2"], string=re.compile(r"Folge\s*\d+", re.IGNORECASE))
    if heading is None:
        heading = next((h for h in soup.find_all(["h1", "h2"]) if re.search(r"Folge\s*\d+", _clean(h.get_text(" ", strip=True)), re.IGNORECASE)), None)
    title = re.sub(r"^TKKG zum Hören\s*[—–-]\s*", "", _clean(discovered["title"]), flags=re.IGNORECASE)
    if heading:
        match = re.search(r"(.+?)\s*\(Folge\s*0*(\d+)\)", _clean(heading.get_text(" ", strip=True)), re.IGNORECASE)
        if match:
            title = _clean(match.group(1))
    text = soup.get_text("\n", strip=True)
    synopsis = None
    paragraph = soup.find("p")
    if paragraph:
        synopsis = _clean(paragraph.get_text(" ", strip=True))
    release = re.search(r"(?:Veröffentlichungsdatum|Veröffentlichung):\s*(\d{1,2}\.\s*[A-Za-zÄÖÜäöü]+\s+\d{4})", text, re.IGNORECASE)
    ean = re.search(r"EAN:\s*([0-9]{8,14})", text, re.IGNORECASE)
    year = None
    if release:
        year_match = re.search(r"(19|20)\d{2}", release.group(1))
        if year_match:
            year = int(year_match.group(0))
    cast = []
    speaker_heading = next((h for h in soup.find_all(["h2", "h3"]) if _clean(h.get_text(" ", strip=True)).casefold() == "sprecher"), None)
    if speaker_heading:
        for item in speaker_heading.find_all_next("li"):
            if item.find(["h2", "h3"]):
                break
            value = _clean(item.get_text(" ", strip=True))
            if " - " in value:
                character, name = value.split(" - ", 1)
                cast.append({"name": _clean(name), "character": _clean(character)})
    tracks = []
    track_heading = next((h for h in soup.find_all(["h2", "h3"]) if "tracks" in _clean(h.get_text(" ", strip=True)).casefold()), None)
    if track_heading:
        for item in track_heading.find_all_next("li"):
            if item.find(["h2", "h3"]):
                break
            value = _clean(item.get_text(" ", strip=True))
            if value:
                tracks.append({"title": re.sub(r"^\d+\.\s*", "", value)})
    image = soup.find("img", src=True)
    image_url = urljoin(discovered["source_url"], image["src"]) if image else None
    physical = []
    if ean or release:
        physical.append({
            "medium": "CD",
            "label": "EUROPA",
            "ean": ean.group(1) if ean else None,
            "release_date": release.group(1) if release else None,
            "source_url": discovered["source_url"],
        })
    return {
        "number": discovered["number"],
        "title": title,
        "synopsis": synopsis,
        "cover_url": image_url,
        "release_date": None,
        "release_year": year,
        "physical_releases": physical,
        "tracks": tracks,
        "cast": cast,
        "credits": [],
        "ratings": [],
        "sources": [{"name": discovered["source_name"], "url": discovered["source_url"]}],
    }
