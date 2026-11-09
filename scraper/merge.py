from __future__ import annotations

from copy import deepcopy


LIST_FIELDS = ("physical_releases", "tracks", "credits", "ratings", "sources", "listening_links")


def merge_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    by_number: dict[int, dict] = {}
    conflicts: list[dict] = []
    for incoming in records:
        number = incoming["number"]
        current = by_number.get(number)
        if current is None:
            current = {
                "number": number,
                "title": incoming["title"],
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
                "sources": [],
                "listening_links": [],
                "last_checked": incoming.get("last_checked"),
            }
            by_number[number] = current
        elif current["title"] != incoming["title"]:
            conflicts.append({
                "number": number,
                "existing_title": current["title"],
                "incoming_title": incoming["title"],
                "incoming_sources": incoming.get("sources", []),
            })
            # Keep the first discovered title. The caller supplies preferred sources first.
        for field in ("synopsis", "cover_url", "release_date", "release_year", "last_checked"):
            if current.get(field) in (None, "") and incoming.get(field) not in (None, ""):
                current[field] = incoming[field]
        # Cast lists are source-specific representations, not complementary
        # fragments. Prefer the first non-empty source (archive records are
        # deliberately passed before official records) to avoid duplicate actors
        # and duplicate character credits from merging two independent lists.
        if not current.get("cast") and incoming.get("cast"):
            current["cast"] = deepcopy(incoming["cast"])

        for field in LIST_FIELDS:
            for item in incoming.get(field, []):
                if item not in current[field]:
                    current[field].append(deepcopy(item))
    return [by_number[key] for key in sorted(by_number)], conflicts
