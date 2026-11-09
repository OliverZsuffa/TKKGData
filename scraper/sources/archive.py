from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from scraper.http import SourceClient


INDEX_URL = "https://www.tkkg-site.de/de/hoeren/hoerspiele/serie.html"
ARCHIVE_PREFIX = "/de/hoeren/hoerspiele/"
ARCHIVE_ORIGIN = "https://www.tkkg-site.de"
EPISODE_LINK = re.compile(r"Folge\s*0*(\d{1,3})\s*:?\s*(.+)", re.IGNORECASE)
HEADING_TAGS = {"h2", "h3", "h4", "h5"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _resolve_index_link(href: str) -> str:
    """Resolve the archive's mixed absolute, root-relative, and directory-relative hrefs."""
    resolved = urljoin(INDEX_URL, href.strip())
    parsed = urlsplit(resolved)
    path = parsed.path

    # Some archive links omit the leading slash, so urljoin treats the site-root
    # path as relative to /de/hoeren/hoerspiele/ and duplicates that directory.
    doubled_prefix = ARCHIVE_PREFIX + ARCHIVE_PREFIX.lstrip("/")
    if path.startswith(doubled_prefix):
        path = ARCHIVE_PREFIX + path[len(doubled_prefix):]

    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def discover_archive_episodes(client: SourceClient) -> list[dict]:
    soup = client.get_html(INDEX_URL)
    records: dict[int, dict] = {}
    for link in soup.find_all("a", href=True):
        label = _clean(link.get_text(" ", strip=True))
        match = EPISODE_LINK.match(label)
        if not match:
            continue
        number = int(match.group(1))
        title = _clean(match.group(2)).lstrip(":").strip()
        if not title or number < 1:
            continue
        url = _resolve_index_link(link["href"])
        if number not in records or (":" in label and "folge-" in url.lower()):
            records[number] = {
                "number": number,
                "title": title,
                "source_url": url,
                "source_name": "TKKG-Site archive",
            }
    return sorted(records.values(), key=lambda item: item["number"])


def _section_lines(soup: BeautifulSoup, heading_text: str) -> list[str]:
    target = next((h for h in soup.find_all(list(HEADING_TAGS)) if _clean(h.get_text(" ", strip=True)).casefold() == heading_text.casefold()), None)
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


def _section_text(soup: BeautifulSoup, heading_text: str) -> str | None:
    result = _clean(" ".join(_section_lines(soup, heading_text)))
    return result or None


def _section_list_items(heading: Tag) -> list[str]:
    items: list[str] = []
    for node in heading.next_elements:
        if isinstance(node, Tag) and node.name in HEADING_TAGS:
            break
        if isinstance(node, Tag) and node.name == "li":
            value = _clean(node.get_text(" ", strip=True))
            if value:
                items.append(re.sub(r"^\d+\.\s*", "", value))
    return items



def _image_candidates(soup: BeautifulSoup, episode_number: int, page_url: str) -> list[str]:
    """Collect explicit episode-cover URLs from markup without guessing filenames."""
    candidates: list[tuple[int, str]] = []

    def add(raw: str | None, score: int) -> None:
        if not raw:
            return
        raw = raw.strip().split()[0]
        if not raw or raw.startswith("data:"):
            return
        # The archive often emits uploads/pics/... without a leading slash.
        # Treat that path as site-root relative, not relative to the episode page.
        if raw.lstrip("/").startswith("uploads/pics/"):
            absolute = urljoin(ARCHIVE_ORIGIN + "/", raw.lstrip("/"))
        else:
            absolute = urljoin(page_url, raw)
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc not in {"www.tkkg-site.de", "tkkg-site.de"}:
            return
        path = parsed.path.casefold()
        filename = path.rsplit("/", 1)[-1]
        if not re.search(rf"(?<!\d)0*{episode_number}(?!\d)", filename) and not re.search(rf"folge\s*0*{episode_number}(?!\d)", raw, re.I):
            return
        if "/uploads/pics/" in path:
            score += 20
        if filename.startswith(str(episode_number).zfill(3)):
            score += 10
        if any(token in path for token in ("avatar", "logo", "icon", "placeholder")):
            return
        candidates.append((score, absolute))

    for image in soup.find_all("img"):
        alt = str(image.get("alt", ""))
        image_score = 10 if re.search(rf"folge\s*0*{episode_number}(?!\d)", alt, re.I) else 0
        for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-image"):
            add(image.get(attr), image_score)
        srcset = image.get("srcset") or image.get("data-srcset")
        if srcset:
            for candidate in srcset.split(","):
                add(candidate.strip().split(" ")[0], image_score)
        parent_link = image.find_parent("a", href=True)
        if parent_link:
            add(parent_link.get("href"), image_score)

    for meta in soup.find_all("meta"):
        if meta.get("property") in {"og:image", "og:image:url"} or meta.get("name") == "twitter:image":
            add(meta.get("content"), 0)

    unique: dict[str, int] = {}
    for score, url in candidates:
        unique[url] = max(score, unique.get(url, -1))
    return [url for url, _ in sorted(unique.items(), key=lambda item: (-item[1], item[0]))]



def _release_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Associate release labels with values in either paired or two-column markup."""
    labels = ("Medium", "Label", "Erscheinungstermin", "EAN")
    label_nodes: dict[str, Tag] = {}
    for label in labels:
        for text_node in soup.find_all(string=True):
            if _clean(str(text_node)).casefold() == f"{label}:".casefold():
                label_nodes[label] = text_node.parent
                break
    if not label_nodes:
        return {}

    # Some archive pages render labels in one column and values in a parallel
    # column. Search upward until the labels share one direct-child column.
    first_node = next(iter(label_nodes.values()))
    first_chain = [first_node, *first_node.parents]
    for common_ancestor in first_chain:
        if not all(any(parent is common_ancestor for parent in node.parents) for node in label_nodes.values()):
            continue
        child_paths = {}
        for label, node in label_nodes.items():
            child = node
            while child.parent is not common_ancestor and child.parent is not None:
                child = child.parent
            child_paths[label] = child
        if len(set(map(id, child_paths.values()))) != 1:
            continue
        label_column = next(iter(child_paths.values()))
        for sibling in common_ancestor.find_all(recursive=False):
            if sibling is label_column:
                continue
            values = [_clean(line) for line in sibling.get_text("\n", strip=True).splitlines()]
            values = [value for value in values if value]
            label_texts = {label.casefold() + ":" for label in labels}
            if len(values) >= len(label_nodes) and not any(value.casefold() in label_texts for value in values):
                return {label: values[index] for index, label in enumerate(label_nodes) if index < len(values)}

    # Some layouts place all labels first and all values immediately after them
    # inside one shared container. Preserve label order even when a label is absent.
    nodes = list(label_nodes.values())
    parents = [node.parent for node in nodes]
    if parents and all(parent is parents[0] for parent in parents) and isinstance(parents[0], Tag):
        siblings = parents[0].find_all(recursive=False)
        positions = [siblings.index(node) for node in nodes if node in siblings]
        if len(positions) == len(nodes) and positions == list(range(min(positions), min(positions) + len(positions))):
            values = [
                _clean(item.get_text(" ", strip=True))
                for item in siblings[max(positions) + 1:]
                if _clean(item.get_text(" ", strip=True))
            ]
            if len(values) >= len(label_nodes):
                return {label: values[index] for index, label in enumerate(label_nodes)}

    # Other pages (and small fixture pages) use adjacent label/value elements.
    result: dict[str, str] = {}
    for label, node in label_nodes.items():
        sibling = node.next_sibling
        while sibling is not None:
            if isinstance(sibling, Tag):
                value = _clean(sibling.get_text(" ", strip=True))
            else:
                value = _clean(str(sibling))
            if value:
                if value.casefold() not in {f"{item.casefold()}:" for item in labels}:
                    result[label] = value
                break
            sibling = sibling.next_sibling
        if label not in result:
            parent = node.parent
            if isinstance(parent, Tag):
                sibling = parent.next_sibling
                while sibling is not None:
                    value = _clean(sibling.get_text(" ", strip=True)) if isinstance(sibling, Tag) else _clean(str(sibling))
                    if value:
                        if value.casefold() not in {f"{item.casefold()}:" for item in labels}:
                            result[label] = value
                        break
                    sibling = sibling.next_sibling
    return result


def parse_archive_episode(client: SourceClient, discovered: dict) -> dict:
    soup = client.get_html(discovered["source_url"])
    heading = soup.find(["h1", "h2"])
    heading_text = _clean(heading.get_text(" ", strip=True)) if heading else discovered["title"]
    title_match = re.match(r"Folge\s*0*\d+\s*:\s*(.+)", heading_text, re.IGNORECASE)
    title = _clean(title_match.group(1)) if title_match else discovered["title"]

    record = {
        "number": discovered["number"],
        "title": title,
        "synopsis": _section_text(soup, "Klappentext"),
        "cover_url": None,
        "release_date": None,
        "release_year": None,
        "physical_releases": [],
        "tracks": [],
        "cast": [],
        "credits": [],
        "ratings": [],
        "sources": [{"name": discovered["source_name"], "url": discovered["source_url"]}],
    }

    candidates = _image_candidates(soup, discovered["number"], discovered["source_url"])
    if candidates:
        record["cover_url"] = candidates[0]

    body_text = soup.get_text("\n", strip=True)
    release_fields = _release_metadata(soup)
    physical = {}
    for source_label, field_name in (
        ("Medium", "medium"),
        ("Label", "label"),
        ("EAN", "ean"),
        ("Erscheinungstermin", "release_date"),
    ):
        value = _clean(release_fields.get(source_label, ""))
        if value and value.casefold() not in {"medium:", "label:", "ean:", "erscheinungstermin:"}:
            physical[field_name] = value
    release_text = physical.get("release_date")
    if release_text:
        year_match = re.search(r"\b(19|20)\d{2}\b", release_text)
        if year_match:
            record["release_year"] = int(year_match.group(0))
    if physical:
        physical["source_url"] = discovered["source_url"]
        record["physical_releases"].append(physical)

    tracks_heading = next((h for h in soup.find_all(list(HEADING_TAGS)) if "trackpunkte" in _clean(h.get_text(" ", strip=True)).casefold() or "cd-tracks" in _clean(h.get_text(" ", strip=True)).casefold()), None)
    if tracks_heading:
        record["tracks"] = [{"title": title} for title in _section_list_items(tracks_heading)]

    speaker_heading = next((h for h in soup.find_all(list(HEADING_TAGS)) if _clean(h.get_text(" ", strip=True)).casefold() == "sprecher"), None)
    if speaker_heading:
        # Speaker credits are represented as definition lists (character in dt,
        # actor in dd). Restrict parsing to those lists immediately following
        # the heading; walking all descendants also traverses the site footer.
        for sibling in speaker_heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in HEADING_TAGS:
                break
            if not isinstance(sibling, Tag):
                continue
            speaker_lists = [sibling] if sibling.name == "dl" else sibling.find_all("dl")
            for speaker_list in speaker_lists:
                for node in speaker_list.find_all("a"):
                    name = _clean(node.get_text(" ", strip=True))
                    if not name:
                        continue
                    dt = node.find_previous("dt")
                    if dt is None or dt.find_parent("dl") is not speaker_list:
                        continue
                    character_text = _clean(dt.get_text(" ", strip=True)).rstrip(":")
                    record["cast"].append({"name": name, "character": character_text or None})

    for line in _section_lines(soup, "Produktion"):
        match = re.match(r"([^:]{2,60}):\s*(.+)", line)
        if match:
            record["credits"].append({"role": _clean(match.group(1)), "name": _clean(match.group(2))})

    ratings_match = re.search(r"Durchschnitts-\s*bewertungen:(.*?)(?:Rang\s*#?(\d+))?", body_text, re.IGNORECASE | re.DOTALL)
    if ratings_match:
        rating_text = _clean(ratings_match.group(1))
        for category, value in re.findall(r"(Team|Mitglieder|Leser|Gesamt)\s*(\d+)%", rating_text, re.IGNORECASE):
            record["ratings"].append({"source": "TKKG-Site archive", "category": category, "value": value + "%", "review_count": None})

    return record
