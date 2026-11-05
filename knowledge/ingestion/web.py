"""Ingestion method 1: scrape web pages.

Downloads one page per URL and keeps the readable text: scripts, styles,
navigation, headers, footers and forms are dropped, and if the page has a
<main> or <article> element only that part is kept. Respects robots.txt.
Uses only the standard library.
"""

from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from .base import IngestionError, Ingestor, RawDocument


USER_AGENT = "cs2340-proj3-ingest/0.1"
TIMEOUT_SECONDS = 15
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form"}
MAIN_TAGS = {"main", "article"}
BLOCK_TAGS = {
    "p", "div", "section", "li", "ul", "ol", "tr", "table", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd",
} | MAIN_TAGS
# Tags that never have a closing tag.
VOID_TAGS = {"br", "img", "hr", "input", "meta", "link", "source", "wbr"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.all_parts = []
        self.main_parts = []
        self._skip_depth = 0
        self._main_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br":
                self._add("\n")
            return
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        if tag in MAIN_TAGS:
            self._main_depth += 1
        if tag in BLOCK_TAGS:
            self._add("\n\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS:
            self._add("\n\n")
        if tag in MAIN_TAGS and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        else:
            self._add(data)

    def _add(self, text):
        if self._skip_depth:
            return
        self.all_parts.append(text)
        if self._main_depth:
            self.main_parts.append(text)


def extract_text(html_text):
    """Return (title, text) from an HTML page. Text keeps paragraph breaks as
    blank lines; tidying whitespace is left to preprocessing."""
    parser = _TextExtractor()
    parser.feed(html_text)
    parser.close()
    main_text = "".join(parser.main_parts)
    text = main_text if main_text.strip() else "".join(parser.all_parts)
    return " ".join(parser.title.split()), text


def robots_allowed(url):
    """Check robots.txt. Fetched with our own user agent: RobotFileParser.read()
    uses Python's default one, which some sites (e.g. Wikipedia) block, and
    it then treats the block as "disallow everything"."""
    parsed = urlparse(url)
    robots = RobotFileParser()
    request = Request(f"{parsed.scheme}://{parsed.netloc}/robots.txt", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            lines = response.read().decode("utf-8", errors="replace").splitlines()
    except HTTPError as exc:
        # Same rules as RobotFileParser.read(): 401/403 = keep out, other errors = no rules.
        return exc.code not in (401, 403)
    except (URLError, TimeoutError, OSError):
        return True  # No reachable robots.txt means no restrictions.
    robots.parse(lines)
    return robots.can_fetch(USER_AGENT, url)


class WebScrapeIngestor(Ingestor):
    method = "web"

    def __init__(self, check_robots=True):
        self.check_robots = check_robots

    def fetch(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise IngestionError(f"{url!r} is not a web address. It should start with http:// or https://.")
        if self.check_robots and not robots_allowed(url):
            raise IngestionError(f"{url} asks scrapers not to visit it (robots.txt), so it was skipped.")

        body, content_type = self._download(url)
        if "html" in content_type:
            title, text = extract_text(body)
        elif content_type.startswith("text/"):
            title, text = "", body
        else:
            raise IngestionError(f"{url} is {content_type}, not a web page or text.")

        yield RawDocument(
            title=title or f"{parsed.netloc}{parsed.path}",
            text=text,
            method=self.method,
            location=url,
            external_id=url,
            metadata={"content_type": content_type},
        )

    def _download(self, url):
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                content_type = response.headers.get_content_type()
                return response.read().decode(charset, errors="replace"), content_type
        except HTTPError as exc:
            raise IngestionError(f"{url} returned HTTP {exc.code} ({exc.reason}).")
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise IngestionError(f"Couldn't reach {url}: {reason}.")
