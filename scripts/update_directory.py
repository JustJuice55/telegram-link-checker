#!/usr/bin/env python3
"""Refresh three bounded public directory cohorts, preserving files on failure."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Direct execution from any working directory, without installing a package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from telegram_link_checker import (  # noqa: E402
    USER_AGENT, MAX_BODY_BYTES, check_links, markdown_text, normalize_telegram_link,
)

COHORTS = (
    ("ru", "jobs", "Russia · Jobs"),
    ("tr", "jobs", "Turkey · Jobs"),
    ("uz", "education", "Uzbekistan · Education"),
)
API_URLS = tuple("https://tgden.com/api/v1/chats?country=" + country + "&category=" + topic +
                 "&sort=relevance&limit=12" for country, topic, _ in COHORTS)
START = "<!-- DIRECTORY:START -->"
END = "<!-- DIRECTORY:END -->"
ATTRIBUTION = "?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map"


class UpdateError(ValueError):
    """A refresh could not produce a complete validated snapshot."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UpdateError("The fixed public API redirected; update aborted.")


def fetch_api(url, *, timeout=10):
    """Read only a fixed allowlisted endpoint; no redirects, auth, or retries."""
    if url not in API_URLS:
        raise UpdateError("Unsupported directory API endpoint.")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Encoding": "identity"})
    with build_opener(_NoRedirects()).open(request, timeout=timeout) as response:
        if response.status != 200 or response.geturl() != url:
            raise UpdateError("Public API response was not a direct HTTP 200.")
        if response.headers.get_content_type() != "application/json":
            raise UpdateError("Public API response is not JSON.")
        body = response.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            raise UpdateError("Public API response exceeds size limit.")
        return json.loads(body.decode("utf-8"))


def validate_cohort(payload, country, topic, source):
    """Validate required public fields and return an explicit output allowlist.

    Additional upstream fields are ignored, never copied to the data or audit.
    A country/topic is an upstream filter, not a verification of geography.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise UpdateError("Public API must return an object with an items array.")
    if not 1 <= len(payload["items"]) <= 12:
        raise UpdateError("Public API cohort must contain 1–12 candidates; empty snapshots are not published.")
    result = []
    for row in payload["items"]:
        if not isinstance(row, dict):
            raise UpdateError("Public API item is not an object.")
        username = row.get("username")
        canonical = normalize_telegram_link("@" + username) if isinstance(username, str) else None
        title = row.get("title")
        count = row.get("members_count")
        categories = row.get("categories")
        if canonical is None:
            raise UpdateError("Public API item has an invalid public username.")
        if (not isinstance(title, str) or not title.strip() or len(title) > 300 or
                any(ord(character) < 32 for character in title)):
            raise UpdateError("Public API item has an invalid title.")
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 10 ** 12:
            raise UpdateError("Public API item has an invalid members_count.")
        if row.get("country") != country or not isinstance(categories, list) or topic not in categories:
            raise UpdateError("Public API item does not match its country/topic filters.")
        if (not all(isinstance(value, str) for value in categories) or
                row.get("is_private") is not False):
            raise UpdateError("Public API item is not explicitly public or has invalid categories.")
        username = canonical.rsplit("/", 1)[1]
        result.append({"username": username, "title": title, "members_count": count,
                       "country": country, "topic": topic, "source": source,
                       "telegram_url": canonical, "tgden_url": "https://tgden.com/en/chat/" + username + ATTRIBUTION})
    return result


def directory_markdown(entries, checks, checked_at):
    counts = {name: sum(check["status"] == name for check in checks)
              for name in ("community_preview", "contact_only", "bot_preview", "inconclusive")}
    lines = [START, "", "### Public community preview directory", "",
             "Checked: **" + checked_at + "** (UTC). " + str(len(entries)) + " listed communities from " + str(len(checks)) + " distinct candidates.",
             "Checks: " + ", ".join(name + "=" + str(count) for name, count in counts.items()) + ".", "",
             "Only previews with member/subscriber evidence are listed. A fresh public preview is not an endorsement or verification of activity, safety, or geography.",
             "Country and topic labels are TGDen's existing source filters. Counts below come from the observed Telegram preview.", ""]
    for country, topic, label in COHORTS:
        cohort_entries = [entry for entry in entries if entry["country"] == country and entry["topic"] == topic]
        lines.extend(["#### " + label + " (" + str(len(cohort_entries)) + ")", "",
                      "| Community | Preview count | Public links |", "| --- | ---: | --- |"])
        for entry in cohort_entries:
            lines.append("| " + markdown_text(entry["title"]) + " | " + format(entry["members_count"], ",") +
                         " | [@" + entry["username"] + "](" + entry["telegram_url"] + ") · [TGDen card](" + entry["tgden_url"] + ") |")
        if not cohort_entries:
            lines.append("| No community previews confirmed in this cohort | — | — |")
        lines.append("")
    lines.extend(["Source: the [TGDen public API](https://tgden.com/api/v1/chats), three cohorts of at most 12 candidates; see [JSON data](data/communities.json) and [check audit](reports/directory-checks.json).",
                  "", END])
    return "\n".join(lines)


def replace_section(readme, section):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise UpdateError("README must contain exactly one pair of directory markers.")
    start = readme.index(START)
    end = readme.index(END)
    if end < start:
        raise UpdateError("README directory markers are out of order.")
    return readme[:start] + section + readme[end + len(END):]


def _atomic_outputs(outputs):
    """Stage everything first; roll back already replaced files on write failure.

    Fetch/validation/classification failures never reach this function. Each file
    replacement is atomic; the rollback handles normal I/O errors. As with any
    multi-file filesystem write, process or machine failure between renames is
    not a multi-file transaction; a later successful run repairs that snapshot.
    """
    staged = {}
    previous = {}
    replaced = []
    try:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            previous[path] = path.read_bytes() if path.exists() else None
            descriptor, temporary = tempfile.mkstemp(prefix=".directory-", dir=path.parent)
            staged[path] = Path(temporary)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except OSError:
        for path in reversed(replaced):
            old = previous[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                descriptor, temporary = tempfile.mkstemp(prefix=".rollback-", dir=path.parent)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(old)
                    os.replace(temporary, path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def update_directory(root=PROJECT_ROOT, *, api_fetcher=None, preview_fetcher=None, checked_at=None, interval=1.0):
    """Refresh all outputs only when every source and distinct preview is conclusive.

    Injectable fetchers support deterministic offline tests. Contact-only and bot
    previews stay in the audit and do not enter the community directory.
    """
    root = Path(root)
    readme_path = root / "README.md"
    # Preserve bytes/newlines outside the markers exactly, including CRLF files.
    readme = readme_path.read_bytes().decode("utf-8")
    replace_section(readme, START + "\n" + END)  # Validate markers before network requests.
    if checked_at is None:
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        parsed_date = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        if parsed_date.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("not UTC")
    except (AttributeError, TypeError, ValueError) as exc:
        raise UpdateError("checked_at must be an ISO timestamp in UTC.") from exc
    api_fetcher = fetch_api if api_fetcher is None else api_fetcher
    candidates = []
    for (country, topic, _), source in zip(COHORTS, API_URLS):
        try:
            payload = api_fetcher(source, timeout=10)
            candidates.extend(validate_cohort(payload, country, topic, source))
        except Exception as exc:
            raise UpdateError("Public API fetch/validation failed (" + type(exc).__name__ + "); previous snapshot retained.") from exc
    distinct_urls = list(dict.fromkeys(candidate["telegram_url"] for candidate in candidates))
    checks = check_links(distinct_urls, fetcher=preview_fetcher, max_links=36, interval=interval)
    for check in checks:
        check["checked_at"] = checked_at
    if any(check["status"] == "inconclusive" for check in checks):
        failed_audit = {"schema_version": 1, "update_status": "aborted", "checked_at": checked_at,
                        "sources": list(API_URLS), "candidate_count": len(candidates),
                        "distinct_previews": len(checks), "listed_count": 0, "checks": checks,
                        "error": "Inconclusive public preview; community data and README retained from previous successful snapshot."}
        _atomic_outputs({root / "reports" / "directory-checks.json":
                         (json.dumps(failed_audit, ensure_ascii=False, indent=2) + "\n").encode("utf-8")})
        raise UpdateError("At least one public preview was inconclusive; previous community data and README retained; attempted checks recorded in audit.")
    by_url = {check["url"]: check for check in checks}
    entries = []
    entry_keys = set()
    for candidate in candidates:
        check = by_url[candidate["telegram_url"]]
        key = (candidate["username"], candidate["country"], candidate["topic"])
        if check["status"] != "community_preview" or key in entry_keys:
            continue
        entry_keys.add(key)
        entry = dict(candidate)
        entry["members_count"] = check["members_count"]
        entry["checked_at"] = checked_at
        entries.append(entry)
    data = {"schema_version": 1, "checked_at": checked_at, "sources": list(API_URLS),
            "cohorts": [{"country": country, "topic": topic, "label": label} for country, topic, label in COHORTS],
            "communities": entries}
    audit = {"schema_version": 1, "update_status": "complete", "checked_at": checked_at, "sources": list(API_URLS),
             "candidate_count": len(candidates), "distinct_previews": len(checks), "listed_count": len(entries), "checks": checks}
    outputs = {
        root / "data" / "communities.json": (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        root / "reports" / "directory-checks.json": (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        readme_path: replace_section(readme, directory_markdown(entries, checks, checked_at)).encode("utf-8"),
    }
    _atomic_outputs(outputs)
    return data, audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Project directory with README directory markers")
    args = parser.parse_args(argv)
    try:
        data, audit = update_directory(args.root)
    except (UpdateError, OSError, UnicodeError) as exc:
        print("Directory update aborted: " + str(exc), file=sys.stderr)
        return 3
    print("Updated " + str(len(data["communities"])) + " entries after " + str(audit["distinct_previews"]) + " distinct public preview checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
