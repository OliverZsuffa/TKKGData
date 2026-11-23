from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data" / "episodes.json"
LEDGER = ROOT / "data" / "audio-discovery-issues.json"


def verified(item: dict[str, Any]) -> bool:
    release = item.get("audio_release")
    return isinstance(release, dict) and release.get("verification", {}).get("status") == "verified"


def audit(episodes: list[dict[str, Any]], ledger_path: Path = LEDGER) -> dict[str, Any]:
    warning = None
    issues: dict[str, Any] = {}
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("issues"), dict):
            raise ValueError("unsupported or malformed ledger structure")
        issues = data["issues"]
    except FileNotFoundError:
        warning = f"Issue ledger missing: {ledger_path}. Prior discovery failures cannot be inferred."
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warning = f"Issue ledger unreadable: {exc}. Prior discovery failures cannot be inferred."

    ready, investigation = [], []
    for item in sorted(episodes, key=lambda x: int(x.get("number", 0))):
        if verified(item):
            continue
        number = str(item.get("number"))
        entry = {"number": item.get("number"), "title": item.get("title", "(title unavailable)")}
        if number in issues:
            entry["issue"] = issues[number]
            investigation.append(entry)
        else:
            ready.append(entry)
    return {"ready_for_discovery": ready, "needs_investigation": investigation, "warning": warning}


def chunks(items: list[dict[str, Any]], size: int = 10) -> list[list[dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def report_text(result: dict[str, Any]) -> str:
    lines = ["# Audio coverage audit", ""]
    if result["warning"]:
        lines += ["**Warning:** " + result["warning"], ""]
    ready = result["ready_for_discovery"]
    investigation = result["needs_investigation"]
    lines += [f"## Ready for discovery ({len(ready)})", ""]
    if ready:
        lines.append("**Episodes to paste into Discover:** " + ", ".join(str(x["number"]) for x in ready))
    else:
        lines.append("No episodes ready for discovery.")
    lines += ["", f"## Needs investigation ({len(investigation)})", ""]
    if investigation:
        lines.append("**Episodes to paste into Discover:** " + ", ".join(str(x["number"]) for x in investigation))
        lines.append("")
        for item in investigation:
            issue = item["issue"]
            lines.append(f"- **{item['number']}: {item['title']}**")
            lines.append(f"  - Last attempt: {issue.get('attempted_at', 'unknown')}")
            lines.append(f"  - Stage/category: {issue.get('stage', 'unknown')} / {issue.get('category', 'unknown')}")
            lines.append(f"  - Reason: {issue.get('reason', 'unknown')}")
            if issue.get("diagnostics"):
                lines.append("  - Diagnostics: " + str(issue["diagnostics"]))
    else:
        lines.append("No episodes currently need investigation.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only TKKG audio coverage audit")
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--json", type=Path, default=Path("audio-coverage-audit.json"))
    parser.add_argument("--markdown", type=Path, default=Path("audio-coverage-audit.md"))
    args = parser.parse_args()
    episodes = json.loads(args.catalogue.read_text(encoding="utf-8"))
    result = audit(episodes, args.ledger)
    text = report_text(result)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(text, encoding="utf-8")
    summary = Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    if summary:
        summary.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
