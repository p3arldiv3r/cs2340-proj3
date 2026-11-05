"""Tests for the ingestion story. Run: python manage.py test knowledge.test_ingestion

No test touches the real internet: web tests replace urlopen with a fake.
"""

import io
import json
import tempfile
from email.message import Message
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from knowledge.ingestion import (
    FileUploadIngestor,
    IngestionError,
    RawDocument,
    WebScrapeIngestor,
    get_ingestor,
)
from knowledge.ingestion.web import extract_text, robots_allowed


SAMPLE_DATA = Path(settings.BASE_DIR) / "sample_data"


class FakeResponse:
    """Stands in for the object urlopen returns."""

    def __init__(self, body, content_type="text/html; charset=utf-8"):
        self._body = body.encode("utf-8")
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class RegistryTests(SimpleTestCase):
    def test_both_methods_are_registered(self):
        self.assertIsInstance(get_ingestor("upload"), FileUploadIngestor)
        self.assertIsInstance(get_ingestor("web"), WebScrapeIngestor)

    def test_unknown_method_raises_plain_error(self):
        with self.assertRaisesMessage(IngestionError, "Unknown ingestion method"):
            get_ingestor("carrier-pigeon")


class FileUploadTests(SimpleTestCase):
    def setUp(self):
        self.ingestor = FileUploadIngestor()

    def fetch(self, file):
        return list(self.ingestor.fetch(file))

    def write_temp(self, name, content):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def test_csv_gives_one_document_per_row(self):
        docs = self.fetch(SAMPLE_DATA / "programs.csv")
        self.assertEqual(len(docs), 5)
        first = docs[0]
        self.assertIsInstance(first, RawDocument)
        self.assertEqual(first.title, "Afternoon Book Circle")
        self.assertEqual(first.external_id, "prog-001")
        self.assertEqual(first.method, "upload")
        self.assertEqual(first.location, "programs.csv")
        self.assertIn("reads one book a month", first.text)
        # Columns that aren't title/id/text are kept as metadata.
        self.assertEqual(first.metadata, {"format": "Online", "time_of_day": "Afternoon", "cost": "Free"})

    def test_json_list_of_records(self):
        docs = self.fetch(SAMPLE_DATA / "programs.json")
        self.assertEqual([d.external_id for d in docs], ["prog-101", "prog-102", "prog-103"])
        self.assertEqual(docs[1].title, "Watercolor Basics")
        self.assertEqual(docs[1].metadata["cost"], "$5 per class")

    def test_json_records_wrapper(self):
        path = self.write_temp("wrapped.json", json.dumps({"records": [{"title": "A", "text": "Some text"}]}))
        self.assertEqual(self.fetch(path)[0].title, "A")

    def test_markdown_heading_becomes_title(self):
        [doc] = self.fetch(SAMPLE_DATA / "book_circle.md")
        self.assertEqual(doc.title, "Afternoon Book Circle: how it works")
        self.assertIn("first Thursday of every month", doc.text)

    def test_text_file_title_falls_back_to_file_name(self):
        [doc] = self.fetch(SAMPLE_DATA / "faq.txt")
        self.assertEqual(doc.title, "Faq")
        self.assertIn("Can I bring a friend?", doc.text)

    def test_uploaded_file_object(self):
        upload = SimpleUploadedFile("notes.txt", b"Uploaded through a Django form.")
        [doc] = self.fetch(upload)
        self.assertEqual(doc.location, "notes.txt")
        self.assertEqual(doc.text, "Uploaded through a Django form.")

    def test_uploaded_file_can_be_read_twice(self):
        upload = SimpleUploadedFile("notes.txt", b"Read me twice.")
        self.fetch(upload)
        self.assertEqual(self.fetch(upload)[0].text, "Read me twice.")

    def test_excel_byte_order_mark_is_ignored(self):
        path = self.write_temp("excel.csv", b"\xef\xbb\xbfTitle,Text\nBOM row,Hello\n")
        [doc] = self.fetch(path)
        self.assertEqual(doc.title, "BOM row")

    def test_csv_headers_are_case_insensitive(self):
        path = self.write_temp("caps.csv", " TITLE ,Body\nUpper,Some body text\n")
        [doc] = self.fetch(path)
        self.assertEqual((doc.title, doc.text), ("Upper", "Some body text"))

    def test_rows_with_empty_text_are_skipped(self):
        path = self.write_temp("gaps.csv", "title,text\nHas text,Hello\nEmpty,\n")
        self.assertEqual([d.title for d in self.fetch(path)], ["Has text"])

    def test_missing_id_and_title_get_defaults(self):
        path = self.write_temp("bare_rows.csv", "text\nFirst\nSecond\n")
        docs = self.fetch(path)
        self.assertEqual([d.external_id for d in docs], ["bare_rows.csv#1", "bare_rows.csv#2"])
        self.assertEqual(docs[0].title, "Bare rows 1")

    def test_csv_without_text_column_is_an_error(self):
        path = self.write_temp("no_text.csv", "title,cost\nA,Free\n")
        with self.assertRaisesMessage(IngestionError, "has no text column"):
            self.fetch(path)

    def test_invalid_json_is_an_error(self):
        path = self.write_temp("broken.json", "{not json")
        with self.assertRaisesMessage(IngestionError, "is not valid JSON"):
            self.fetch(path)

    def test_json_that_is_not_records_is_an_error(self):
        path = self.write_temp("numbers.json", "[1, 2, 3]")
        with self.assertRaisesMessage(IngestionError, "list of records"):
            self.fetch(path)

    def test_unsupported_file_type_is_an_error(self):
        path = self.write_temp("slides.pptx", b"binary")
        with self.assertRaisesMessage(IngestionError, "supported file types are"):
            self.fetch(path)

    def test_missing_file_is_an_error(self):
        with self.assertRaisesMessage(IngestionError, "File not found"):
            self.fetch(SAMPLE_DATA / "does_not_exist.csv")


class ExtractTextTests(SimpleTestCase):
    def test_sample_page_keeps_only_main_content(self):
        title, text = extract_text((SAMPLE_DATA / "sample_page.html").read_text(encoding="utf-8"))
        self.assertEqual(title, "Garden Walk Club | Sample Community Network")
        self.assertIn("Garden Walk Club", text)
        self.assertIn("tea & conversation", text)  # entity decoded
        self.assertIn("$2 per walk", text)
        for junk in ("console.log", "font-family", "Programs", "Contact", "newsletter", "©"):
            self.assertNotIn(junk, text)

    def test_paragraphs_are_separated_by_blank_lines(self):
        _, text = extract_text("<main><p>One</p><p>Two</p></main>")
        self.assertRegex(text, r"One\s*\n\s*\n\s*Two")

    def test_br_becomes_line_break(self):
        _, text = extract_text("<p>Line one<br>Line two</p>")
        self.assertIn("Line one\nLine two", text)

    def test_page_without_main_keeps_body_text_minus_chrome(self):
        _, text = extract_text("<body><nav>Menu</nav><p>Body text</p><footer>Foot</footer></body>")
        self.assertIn("Body text", text)
        self.assertNotIn("Menu", text)
        self.assertNotIn("Foot", text)


@mock.patch("knowledge.ingestion.web.robots_allowed", return_value=True)
class WebScrapeTests(SimpleTestCase):
    def setUp(self):
        self.ingestor = WebScrapeIngestor()

    def fetch(self, url):
        return list(self.ingestor.fetch(url))

    def test_scrapes_page_into_one_document(self, _robots):
        html = (SAMPLE_DATA / "sample_page.html").read_text(encoding="utf-8")
        with mock.patch("knowledge.ingestion.web.urlopen", return_value=FakeResponse(html)) as urlopen:
            [doc] = self.fetch("https://example.org/garden-walk")
        self.assertEqual(doc.method, "web")
        self.assertEqual(doc.location, "https://example.org/garden-walk")
        self.assertEqual(doc.external_id, "https://example.org/garden-walk")
        self.assertEqual(doc.title, "Garden Walk Club | Sample Community Network")
        self.assertIn("step-free", doc.text)
        self.assertEqual(doc.metadata["content_type"], "text/html")
        # Identifies itself with our user agent.
        request = urlopen.call_args.args[0]
        self.assertTrue(request.get_header("User-agent").startswith("cs2340-proj3"))

    def test_page_without_title_uses_url(self, _robots):
        with mock.patch("knowledge.ingestion.web.urlopen", return_value=FakeResponse("<p>Hi</p>")):
            [doc] = self.fetch("https://example.org/no-title")
        self.assertEqual(doc.title, "example.org/no-title")

    def test_plain_text_page_kept_as_is(self, _robots):
        response = FakeResponse("Just text.", content_type="text/plain")
        with mock.patch("knowledge.ingestion.web.urlopen", return_value=response):
            [doc] = self.fetch("https://example.org/notes.txt")
        self.assertEqual(doc.text, "Just text.")

    def test_non_text_content_is_an_error(self, _robots):
        response = FakeResponse("%PDF", content_type="application/pdf")
        with mock.patch("knowledge.ingestion.web.urlopen", return_value=response):
            with self.assertRaisesMessage(IngestionError, "not a web page"):
                self.fetch("https://example.org/file.pdf")

    def test_http_error_is_a_plain_error(self, _robots):
        error = HTTPError("https://example.org/gone", 404, "Not Found", {}, None)
        with mock.patch("knowledge.ingestion.web.urlopen", side_effect=error):
            with self.assertRaisesMessage(IngestionError, "returned HTTP 404"):
                self.fetch("https://example.org/gone")

    def test_unreachable_site_is_a_plain_error(self, _robots):
        with mock.patch("knowledge.ingestion.web.urlopen", side_effect=URLError("no route")):
            with self.assertRaisesMessage(IngestionError, "Couldn't reach"):
                self.fetch("https://example.invalid/")

    def test_non_web_address_is_rejected(self, _robots):
        for bad in ("ftp://example.org/x", "example.org", "file:///etc/passwd"):
            with self.subTest(bad=bad), self.assertRaisesMessage(IngestionError, "not a web address"):
                self.fetch(bad)

    def test_robots_txt_disallow_is_respected(self, robots):
        robots.return_value = False
        with mock.patch("knowledge.ingestion.web.urlopen") as urlopen:
            with self.assertRaisesMessage(IngestionError, "robots.txt"):
                self.fetch("https://example.org/private")
        urlopen.assert_not_called()

    def test_robots_check_can_be_turned_off(self, robots):
        robots.return_value = False
        ingestor = WebScrapeIngestor(check_robots=False)
        with mock.patch("knowledge.ingestion.web.urlopen", return_value=FakeResponse("<p>Hi</p>")):
            self.assertEqual(len(list(ingestor.fetch("https://example.org/mine"))), 1)


class RobotsTxtTests(SimpleTestCase):
    ROBOTS = "User-agent: *\nDisallow: /private/\n"

    def allowed(self, url, **urlopen_kwargs):
        with mock.patch("knowledge.ingestion.web.urlopen", **urlopen_kwargs) as urlopen:
            result = robots_allowed(url)
        return result, urlopen

    def test_follows_disallow_rules(self):
        response = FakeResponse(self.ROBOTS, content_type="text/plain")
        self.assertTrue(self.allowed("https://example.org/public", return_value=response)[0])
        response = FakeResponse(self.ROBOTS, content_type="text/plain")
        self.assertFalse(self.allowed("https://example.org/private/page", return_value=response)[0])

    def test_fetches_robots_with_our_user_agent(self):
        response = FakeResponse(self.ROBOTS, content_type="text/plain")
        _, urlopen = self.allowed("https://example.org/page", return_value=response)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.org/robots.txt")
        self.assertTrue(request.get_header("User-agent").startswith("cs2340-proj3"))

    def test_missing_robots_txt_allows_everything(self):
        error = HTTPError("https://example.org/robots.txt", 404, "Not Found", {}, None)
        self.assertTrue(self.allowed("https://example.org/page", side_effect=error)[0])

    def test_forbidden_robots_txt_disallows(self):
        error = HTTPError("https://example.org/robots.txt", 403, "Forbidden", {}, None)
        self.assertFalse(self.allowed("https://example.org/page", side_effect=error)[0])

    def test_unreachable_robots_txt_allows(self):
        self.assertTrue(self.allowed("https://example.org/page", side_effect=URLError("down"))[0])


class PreviewCommandTests(SimpleTestCase):
    def run_command(self, *args):
        out = io.StringIO()
        call_command("preview_ingest", *args, stdout=out)
        return out.getvalue()

    def test_preview_upload(self):
        output = self.run_command("upload", str(SAMPLE_DATA / "programs.csv"))
        self.assertIn("5 document(s)", output)
        self.assertIn("Afternoon Book Circle", output)

    def test_preview_several_files(self):
        output = self.run_command("upload", str(SAMPLE_DATA / "programs.csv"), str(SAMPLE_DATA / "programs.json"))
        self.assertIn("Total: 8 document(s)", output)

    def test_json_export(self):
        with tempfile.TemporaryDirectory() as directory:
            out_path = Path(directory) / "out.json"
            self.run_command("upload", str(SAMPLE_DATA / "programs.json"), "--json", str(out_path))
            exported = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(len(exported), 3)
        self.assertEqual(
            set(exported[0]), {"title", "text", "method", "location", "external_id", "metadata"}
        )

    def test_errors_are_reported_without_a_traceback(self):
        with self.assertRaisesMessage(CommandError, "File not found"):
            self.run_command("upload", "nope.csv")
