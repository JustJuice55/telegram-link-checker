"""Conservative checks of public Telegram web previews; Python standard library only.

A result describes the HTML observed, never whether a username is deleted or banned.
No Telegram authentication, client API, bot API, or community joins are used.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

USER_AGENT = "TelegramLinkChecker/0.1 (+https://github.com/JustJuice55/telegram-link-checker)"
MAX_BODY_BYTES = 512 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_LINKS = 200
MAX_REDIRECTS = 3
USERNAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{2,31}\Z", re.ASCII)
RESERVED = frozenset({
    "addemoji", "addlist", "addstickers", "addtheme", "boost", "confirmphone",
    "contact", "giftcode", "invoice", "joinchat", "login", "proxy", "setlanguage",
    "share", "socks", "iv", "nft", "passport", "resolve", "s", "c",
})
STATUSES = ("community_preview", "contact_only", "bot_preview", "inconclusive")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_telegram_link(value):
    """Return a canonical HTTPS public username URL, or None for unsupported input.

    Query parameters are discarded. Only /username and /s/username are supported;
    private invites, message links, credentials, ports, encoded paths, and other
    Telegram services are deliberately excluded.
    """
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.startswith("@"):
        name = value[1:]
    else:
        try:
            parts = urlsplit(value)
            if (parts.scheme.lower() != "https" or
                    parts.netloc.lower() not in {"t.me", "telegram.me"} or
                    any(ord(char) < 33 for char in value)):
                return None
            segments = parts.path.strip("/").split("/")
            # A single optional trailing slash is harmless, but repeated slashes
            # are not a canonical public username path.
            if parts.path != "/" + "/".join(segments) and parts.path != "/" + "/".join(segments) + "/":
                return None
            if len(segments) == 2 and segments[0] == "s":
                name = segments[1]
            elif len(segments) == 1:
                name = segments[0]
            else:
                return None
        except (ValueError, TypeError):
            return None
    if not USERNAME.fullmatch(name) or name.lower() in RESERVED:
        return None
    return "https://t.me/" + name.lower()


def extract_links(text):
    """Extract deduplicated supported public Telegram URLs from Markdown text.

    Bare @handles in prose are intentionally ignored: they may be people or email
    fragments. Positional @handles are accepted explicitly by the CLI.
    """
    found = []
    for match in re.finditer(r"https://(?:t\.me|telegram\.me)/[^\s<>\[\]\"'`]+", text, re.IGNORECASE):
        candidate = match.group(0).rstrip(".,;:!?)")
        normalized = normalize_telegram_link(candidate)
        if normalized and normalized not in found:
            found.append(normalized)
    return found


def _clean(text):
    return " ".join(text.split())


class _PreviewParser(HTMLParser):
    VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.og_title = ""
        self.parts = {"extra": [], "description": [], "action": [], "title": [], "page_title": []}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property", "").lower() == "og:title":
            self.og_title = attrs.get("content", "")
        if tag not in self.VOID:
            self.stack.append((tag, set(attrs.get("class", "").split())))
        elif tag == "br":
            self.handle_data(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if any(tag in {"script", "style", "noscript"} for tag, _ in self.stack):
            return
        classes = set().union(*(classes for _, classes in self.stack)) if self.stack else set()
        for key, class_name in (("extra", "tgme_page_extra"),
                                ("description", "tgme_page_description"),
                                ("title", "tgme_page_title")):
            if class_name in classes:
                self.parts[key].append(data)
        if {"tgme_action_button", "tgme_action_button_new"} & classes:
            self.parts["action"].append(data)
        if any(tag == "title" for tag, _ in self.stack):
            self.parts["page_title"].append(data)


def classify_preview(body, status_code=200):
    """Classify concrete HTML evidence from a bounded public preview response."""
    result = {"status": "inconclusive", "title": "", "members_count": None,
              "evidence": "No supported public preview evidence found."}
    if status_code != 200:
        result["evidence"] = "HTTP response status " + str(status_code) + "; preview unavailable."
        return result
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BODY_BYTES:
        result["evidence"] = "Preview body missing or exceeds size limit."
        return result
    parser = _PreviewParser()
    try:
        parser.feed(body)
        parser.close()
    except (ValueError, RecursionError):
        result["evidence"] = "Unsupported preview HTML."
        return result
    sections = {key: _clean("".join(value)) for key, value in parser.parts.items()}
    title = _clean(parser.og_title or sections["title"])
    result["title"] = title[:300]
    challenge_title = sections["page_title"].casefold()
    if (any(marker in body.casefold() for marker in ("cf-chl-", "challenge-platform")) or
            any(marker in challenge_title for marker in ("just a moment", "captcha", "verify you are human", "checking your browser"))):
        result["evidence"] = "Challenge page observed; public preview could not be checked."
        return result
    if re.search(r"\bstart\s+bot\b", sections["action"], re.IGNORECASE):
        result.update(status="bot_preview", evidence="Start Bot action observed in the Telegram preview.")
        return result
    member_match = re.search(r"(?<![\w.])([0-9]+(?:[ ,\u00a0\u202f][0-9]{3})*)\s+(members?|subscribers?)\b",
                             sections["extra"], re.IGNORECASE)
    if member_match:
        count = int(re.sub(r"[^0-9]", "", member_match.group(1)))
        if count > 10 ** 12:
            result["evidence"] = "Unsupported community count in preview."
            return result
        result.update(status="community_preview", members_count=count,
                      evidence="tgme_page_extra contains: " + member_match.group(0))
        return result
    description = sections["description"].casefold()
    if "you can contact" in description and "telegram" in description:
        result.update(status="contact_only", evidence="Generic Telegram contact prompt observed; community membership evidence absent.")
    return result


class UnsafeRedirect(ValueError):
    """A redirect left the supported public Telegram username surface."""


class _TelegramRedirects(HTTPRedirectHandler):
    def __init__(self, limiter=None):
        super().__init__()
        self.limiter = limiter

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalized = normalize_telegram_link(urljoin(req.full_url, newurl))
        if normalized is None:
            raise UnsafeRedirect("Redirect target is not a supported HTTPS public Telegram username.")
        redirect_count = getattr(req, "telegram_redirect_count", 0) + 1
        if redirect_count > MAX_REDIRECTS:
            raise UnsafeRedirect("Public preview redirect limit reached.")
        redirected = super().redirect_request(req, fp, code, msg, headers, normalized)
        if redirected is not None:
            if self.limiter is not None:
                self.limiter.wait()
            redirected.telegram_redirect_count = redirect_count
        return redirected


@dataclass(frozen=True)
class FetchResponse:
    body: str
    status_code: int = 200
    final_url: str = ""


def fetch_preview(url, *, timeout=10, limiter=None):
    """Fetch at most 512 KiB, validating every redirect before following it.

    There are no retries. TLS uses Python's default certificate verification.
    """
    canonical = normalize_telegram_link(url)
    if canonical is None:
        raise ValueError("Unsupported public Telegram URL.")
    if not 0 < timeout <= 10:
        raise ValueError("Request timeout must be greater than zero and at most 10 seconds.")
    request = Request(canonical, headers={"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "identity"})
    limiter = _RateLimiter(1.0) if limiter is None else limiter
    limiter.wait()
    opener = build_opener(_TelegramRedirects(limiter))
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        return FetchResponse("", exc.code, canonical)
    with response:
        final_url = normalize_telegram_link(response.geturl())
        if final_url is None:
            raise UnsafeRedirect("Unsupported final preview URL.")
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("Unsupported preview content type.")
        body = response.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("Preview body exceeds size limit.")
        return FetchResponse(body.decode("utf-8", errors="replace"), response.status, final_url)


class _RateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait(self):
        with self.lock:
            delay = max(0.0, self.next_start - time.monotonic())
            if delay:
                time.sleep(delay)
            self.next_start = time.monotonic() + self.interval


def check_links(links, *, fetcher=None, workers=2, timeout=10, interval=1.0, max_links=MAX_LINKS):
    """Check deduplicated URLs in input order; inject fetcher(url, timeout=...) offline.

    The fetcher returns FetchResponse. At most two concurrent checks and 200
    distinct inputs are accepted. The default global start rate is one/second.
    Redirect requests are independently bounded to three per input.
    """
    if workers not in (1, 2) or not 0 < timeout <= 10 or not 0 <= interval <= 60:
        raise ValueError("Workers must be 1 or 2; timeout 0–10 seconds; interval 0–60 seconds.")
    if not 1 <= max_links <= MAX_LINKS:
        raise ValueError("Maximum links must be between 1 and 200.")
    urls = []
    for link in links:
        canonical = normalize_telegram_link(link)
        if canonical is None:
            raise ValueError("Unsupported public Telegram URL or handle: " + str(link))
        if canonical not in urls:
            urls.append(canonical)
        if len(urls) > max_links:
            raise ValueError("Input exceeds the distinct URL limit of " + str(max_links) + ".")
    limiter = _RateLimiter(interval)

    def check_one(url):
        try:
            if fetcher is None:
                response = fetch_preview(url, timeout=timeout, limiter=limiter)
            else:
                limiter.wait()
                response = fetcher(url, timeout=timeout)
            if not isinstance(response, FetchResponse):
                raise TypeError("Fetcher must return FetchResponse.")
            if response.final_url and normalize_telegram_link(response.final_url) is None:
                raise UnsafeRedirect("Unsupported final preview URL.")
            result = classify_preview(response.body, response.status_code)
            result["http_status"] = response.status_code
        except Exception as exc:
            # Error text can include URL credentials or arbitrary remote content;
            # expose only a stable type, never exception strings.
            result = {"status": "inconclusive", "title": "", "members_count": None,
                      "http_status": None, "evidence": "Preview request failed (" + type(exc).__name__ + ")."}
        result.update(url=url, checked_at=utc_now())
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(check_one, urls))


def markdown_text(value):
    """Escape remote text so it cannot introduce HTML, links, or table cells."""
    value = escape(_clean(str(value)), quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>-])", r"\\\1", value)


def markdown_report(results):
    lines = ["## Telegram public preview checks", "", "| Public URL | Status | Evidence |", "| --- | --- | --- |"]
    for result in results:
        url = result["url"]
        lines.append("| [" + markdown_text(url.rsplit("/", 1)[-1]) + "](" + url + ") | " +
                     result["status"] + " | " + markdown_text(result["evidence"]) + " |")
    lines.extend(["", "A preview is an observation, not proof of activity, location, safety, or endorsement.",
                  "A generic contact prompt does not establish account or community availability.", ""])
    return "\n".join(lines)


def exit_code(results, fail_on_contact=False):
    """0=completed, 1=contact policy failure, 3=inconclusive (takes precedence)."""
    if any(result["status"] == "inconclusive" for result in results):
        return 3
    if fail_on_contact and any(result["status"] == "contact_only" for result in results):
        return 1
    return 0


def main(argv=None, *, fetcher=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("links", nargs="*", help="HTTPS t.me/telegram.me public URLs or explicit @handles")
    parser.add_argument("--file", type=Path, help="Local Markdown file (up to 2 MiB)")
    parser.add_argument("--json", type=Path, dest="json_path", help="Write JSON report")
    parser.add_argument("--markdown", type=Path, help="Write Markdown report")
    parser.add_argument("--fail-on-contact", action="store_true", help="Exit 1 on contact_only; inconclusive exits 3")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--interval", type=float, default=1, help="Global seconds between requests (minimum 1)")
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 10 or not 1 <= args.interval <= 60:
        parser.error("--timeout must be 0–10 seconds and --interval 1–60 seconds")
    try:
        links = list(args.links)
        if args.file:
            with args.file.open("rb") as stream:
                content = stream.read(MAX_FILE_BYTES + 1)
            if len(content) > MAX_FILE_BYTES:
                raise ValueError("Markdown input exceeds the 2 MiB limit.")
            links.extend(extract_links(content.decode("utf-8")))
        if not links:
            raise ValueError("No supported public Telegram links found.")
        results = check_links(links, fetcher=fetcher, workers=args.workers, timeout=args.timeout, interval=args.interval)
        report = {"schema_version": 1, "checked_at": utc_now(), "results": results}
        rendered_json = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.json_path:
            args.json_path.write_text(rendered_json, encoding="utf-8")
        if args.markdown:
            args.markdown.write_text(markdown_report(results), encoding="utf-8")
        if not args.json_path and not args.markdown:
            sys.stdout.write(rendered_json)
        return exit_code(results, args.fail_on_contact)
    except (OSError, ValueError, UnicodeError) as exc:
        print("Input/report error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
