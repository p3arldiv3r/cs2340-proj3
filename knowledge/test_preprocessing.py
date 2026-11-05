"""Tests for the preprocessing story. Run: python manage.py test knowledge.test_preprocessing"""

import io
import re
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from knowledge.preprocessing import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_text,
    clean_text,
    content_hash,
    is_useful,
    preprocess,
)


SAMPLE_DATA = Path(settings.BASE_DIR) / "sample_data"


def words(text):
    return re.findall(r"\S+", text)


class CleanTextTests(SimpleTestCase):
    def test_empty_input(self):
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")

    def test_html_entities_are_decoded(self):
        self.assertEqual(clean_text("Tea &amp; talk, 5 &lt; 6"), "Tea & talk, 5 < 6")

    def test_leftover_tags_are_removed(self):
        self.assertEqual(clean_text("<p>Hello <b>there</b></p>"), "Hello there")

    def test_unicode_is_normalized(self):
        # non-breaking space, "fi" ligature, full-width letters
        self.assertEqual(clean_text("3:00 PM ﬁne ＡＢ"), "3:00 PM fine AB")

    def test_curly_quotes_and_hyphens_become_ascii(self):
        self.assertEqual(
            clean_text("“It’s one‑on‑one,” 3–4"),
            "\"It's one-on-one,\" 3-4",
        )

    def test_em_dash_is_kept(self):
        self.assertEqual(clean_text("Calm — and kind"), "Calm — and kind")

    def test_invisible_and_control_characters_are_removed(self):
        self.assertEqual(clean_text("li​brary­ room\x07﻿"), "library room")

    def test_whitespace_is_collapsed_and_lines_trimmed(self):
        self.assertEqual(clean_text("  Tech \t  Help   Hour  "), "Tech Help Hour")

    def test_windows_line_endings(self):
        self.assertEqual(clean_text("One\r\nTwo\rThree"), "One\nTwo\nThree")

    def test_paragraph_breaks_collapse_to_one_blank_line(self):
        self.assertEqual(clean_text("One\n\n\n\n\nTwo\n \n\t\nThree"), "One\n\nTwo\n\nThree")

    def test_boilerplate_lines_are_dropped(self):
        for line in (
            "Skip to main content",
            "Accept all cookies",
            "We use cookies to improve your experience.",
            "Menu",
            "Share this page",
            "Follow us on Facebook",
            "Back to top",
            "Privacy Policy",
            "© 2026 Sample Community Network",
            "Copyright 2026 Example Inc.",
            "Example Inc. All rights reserved.",
        ):
            with self.subTest(line=line):
                self.assertEqual(clean_text(f"Real content here.\n{line}"), "Real content here.")

    def test_real_sentences_that_mention_boilerplate_words_are_kept(self):
        for line in (
            "Subscribe to updates at the front desk.",
            "Copyright law can be confusing; our volunteers can explain the basics.",
            "Search for a group by topic using the Find button.",
            "Share your favorite recipe at the potluck.",
        ):
            with self.subTest(line=line):
                self.assertEqual(clean_text(line), line)

    def test_long_lines_are_never_treated_as_boilerplate(self):
        line = "© " + "real words " * 20
        self.assertIn("real words", clean_text(line))

    def test_lines_without_letters_or_digits_are_dropped(self):
        self.assertEqual(clean_text("Title\n----------\n| | |\n***\nBody"), "Title\nBody")

    def test_repeated_line_is_dropped(self):
        self.assertEqual(clean_text("Garden Walk\nGarden Walk\n\nGarden Walk\nDetails"), "Garden Walk\n\nDetails")

    def test_non_consecutive_repeats_are_kept(self):
        self.assertEqual(clean_text("Free\nOnline\nFree"), "Free\nOnline\nFree")

    def test_cleaning_twice_changes_nothing(self):
        raw = (SAMPLE_DATA / "messy_page.txt").read_text(encoding="utf-8")
        once = clean_text(raw)
        self.assertEqual(clean_text(once), once)

    def test_messy_sample_page(self):
        cleaned = clean_text((SAMPLE_DATA / "messy_page.txt").read_text(encoding="utf-8"))
        self.assertTrue(cleaned.startswith("Tech Help Hour & Q&A\n\nBring your phone"))
        self.assertEqual(cleaned.count("Tech Help Hour"), 1)
        self.assertIn("library's community room", cleaned)
        self.assertIn("1:00 to 3:00 PM", cleaned)
        for junk in ("Skip to", "cookies", "Menu", "---", "Share this", "Follow us", "©", "<p>", "&amp;", "​"):
            self.assertNotIn(junk, cleaned)

    def test_share_buttons_and_feedback_widget_are_dropped(self):
        # Layout of the end of the real CDC page, saved from Chrome.
        tail = (
            "Join a community garden.\n\nSources and Page Info\n\nFacebook\n\nLinkedIn\n\nTwitter\n\nSyndicate\n\n"
            "Was this page helpful?\n\nThank you for your feedback!\n\n"
            "How would you rate this information?\n\nNot helpful\nVery helpful\n\nRelated Pages\n\nView All"
        )
        self.assertEqual(clean_text(tail), "Join a community garden.\n\nSources and Page Info")

    def test_bare_yes_and_no_answers_are_kept(self):
        faq = "Is there a cost?\nNo.\n\nCan I bring a friend?\nYes!"
        self.assertEqual(clean_text(faq), faq)

    def test_learn_more_links_are_dropped(self):
        self.assertEqual(clean_text("1 in 6 people are lonely.\nLearn more\nRead more."), "1 in 6 people are lonely.")


class ResearchArticleTests(SimpleTestCase):
    """Rules added after checking the team's real PubMed Central articles.
    sample_data/research_article.txt copies their layout with made-up content."""

    def setUp(self):
        self.raw = (SAMPLE_DATA / "research_article.txt").read_text(encoding="utf-8")
        self.cleaned = clean_text(self.raw)

    def test_article_content_is_kept(self):
        for text in (
            "Weekly online book groups and loneliness in older adults: a pilot study",
            "Loneliness scores fell by an average of 12 percent.",
            "Short, regular online groups are a promising, low-cost way to reduce loneliness.",
        ):
            self.assertIn(text, self.cleaned)

    def test_reference_list_and_everything_after_it_is_dropped(self):
        for text in ("References", "Lee K, Patel R", "Book clubs as community", "Supplementary Materials", "Click here"):
            self.assertNotIn(text, self.cleaned)
        self.assertTrue(self.cleaned.endswith("Contributor Information\n\nSam Okafor."))

    def test_article_chrome_lines_are_dropped(self):
        for text in ("Find articles by", "Author information", "Article notes",
                     "Copyright and License information", "PMC Copyright notice"):
            self.assertNotIn(text, self.cleaned)

    def test_emails_are_removed_with_their_label(self):
        self.assertNotIn("@", self.cleaned)
        self.assertNotIn("Email", self.cleaned)
        self.assertIn("Alex Rivera, Department of Sample Studies, Example University.", self.cleaned)

    def test_cleaning_twice_changes_nothing(self):
        self.assertEqual(clean_text(self.cleaned), self.cleaned)

    def test_citation_badges_are_removed_anywhere(self):
        self.assertEqual(
            clean_text("As shown before [DOI] [PubMed] [Google Scholar] [PMC free article] [CrossRef]."),
            "As shown before .",
        )

    def test_references_can_be_kept(self):
        cleaned = clean_text(self.raw, drop_references=False)
        self.assertIn("References", cleaned)
        self.assertIn("Video calls and wellbeing among older adults.", cleaned)
        self.assertNotIn("[PubMed]", cleaned)  # badges still go

    def test_heading_followed_by_prose_is_not_cut(self):
        text = (
            "Our guide to staying connected.\n\nReferences\n\n"
            "Ask the front desk for printed copies of any guide.\n"
            "Volunteers can help you find the right group.\n"
            "Large-print versions are available on request."
        )
        self.assertEqual(clean_text(text), text)

    def test_only_the_last_references_heading_counts(self):
        text = (
            "Contents\nIntroduction\nReferences\n\nIntroduction\n\nGroups help people feel connected.\n"
            "Many groups meet online.\nSome meet in person.\n\nReferences\n\n"
            "1.Lee K, et al. 2019.\n2.Nguyen T. 2021. doi: 10.0000/x\n3.Garcia M, et al. 2020."
        )
        cleaned = clean_text(text)
        self.assertIn("Some meet in person.", cleaned)
        self.assertNotIn("Lee K", cleaned)
        self.assertTrue(cleaned.startswith("Contents\nIntroduction\nReferences"))  # table of contents kept

    def test_tiny_references_section_is_not_cut(self):
        text = "Main text about groups.\n\nReferences\n\nLee K, 2019."
        self.assertEqual(clean_text(text), text)


class EmailTests(SimpleTestCase):
    def test_bare_address_and_labels(self):
        self.assertEqual(clean_text("Contact the organizer at sam@example.org today."), "Contact the organizer at today.")
        self.assertEqual(clean_text("Min Liu, Email: min@example.org."), "Min Liu.")
        self.assertEqual(clean_text("Questions? E-mail: help@example.org"), "Questions?")

    def test_line_of_only_addresses_is_dropped(self):
        self.assertEqual(clean_text("Body.\nEmail: a@example.org; b@example.com"), "Body.")

    def test_emails_can_be_kept(self):
        line = "Email the organizer: sam@example.org"
        self.assertEqual(clean_text(line, remove_emails=False), line)

    def test_at_signs_that_are_not_emails_are_kept(self):
        self.assertEqual(clean_text("Meet @ the library, 2 tickets @ $5."), "Meet @ the library, 2 tickets @ $5.")


class IsUsefulTests(SimpleTestCase):
    def test_real_content_is_useful(self):
        self.assertTrue(is_useful("The book circle meets on the first Thursday of every month."))

    def test_too_short_or_only_boilerplate_is_not_useful(self):
        self.assertFalse(is_useful("Hi"))
        self.assertFalse(is_useful("Skip to main content\nMenu\n© 2026 Example\n----"))
        self.assertFalse(is_useful("1234567890 " * 10))  # no letters

    def test_threshold_can_be_changed(self):
        self.assertTrue(is_useful("Hi there", min_chars=5))


class ContentHashTests(SimpleTestCase):
    def test_same_content_with_different_spacing_or_case_matches(self):
        self.assertEqual(content_hash("Garden Walk Club\n\nMeets Tuesdays."), content_hash("garden  walk club meets tuesdays."))

    def test_same_content_with_different_boilerplate_matches(self):
        self.assertEqual(content_hash("Skip to content\nMeets Tuesdays."), content_hash("Meets Tuesdays."))

    def test_different_content_differs(self):
        self.assertNotEqual(content_hash("Meets Tuesdays."), content_hash("Meets Wednesdays."))

    def test_hash_is_hex_sha256(self):
        self.assertRegex(content_hash("x"), r"^[0-9a-f]{64}$")


class ChunkTextTests(SimpleTestCase):
    def long_text(self, paragraphs=12, sentences=6):
        return "\n\n".join(
            " ".join(f"Paragraph {p} sentence {s} talks about group activities." for s in range(sentences))
            for p in range(paragraphs)
        )

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk_text("Just one short paragraph."), ["Just one short paragraph."])

    def test_empty_text_has_no_chunks(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("\n\n \n\n"), [])

    def test_defaults(self):
        self.assertEqual((CHUNK_SIZE, CHUNK_OVERLAP), (800, 120))

    def test_no_chunk_is_longer_than_size(self):
        text = self.long_text()
        for size, overlap in ((800, 120), (300, 60), (100, 0), (50, 49)):
            with self.subTest(size=size, overlap=overlap):
                chunks = chunk_text(text, size=size, overlap=overlap)
                self.assertGreater(len(chunks), 1)
                self.assertTrue(all(len(c) <= size for c in chunks), [len(c) for c in chunks])

    def test_no_words_are_lost_or_cut(self):
        text = self.long_text()
        for size, overlap in ((300, 60), (100, 0)):
            with self.subTest(size=size):
                chunks = chunk_text(text, size=size, overlap=overlap)
                original = words(text)
                chunk_words = [w for c in chunks for w in words(c)]
                # Every chunked word is a real word from the text (nothing cut in half)...
                self.assertTrue(set(chunk_words) <= set(original))
                # ...and every word appears, in order, once overlap is removed.
                if overlap == 0:
                    self.assertEqual(chunk_words, original)

    def test_splits_between_paragraphs_when_possible(self):
        paragraphs = [("A" * 10 + " ") * 23, ("B" * 10 + " ") * 23, ("C" * 10 + " ") * 23]  # ~250 chars each
        text = "\n\n".join(p.strip() for p in paragraphs)
        chunks = chunk_text(text, size=400, overlap=0)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[0].startswith("A") and chunks[0].endswith("A"))
        self.assertTrue(chunks[1].startswith("B"))

    def test_small_paragraphs_are_packed_together(self):
        text = "One.\n\nTwo.\n\nThree."
        self.assertEqual(chunk_text(text, size=100, overlap=0), ["One.\n\nTwo.\n\nThree."])

    def test_long_paragraph_splits_at_sentences(self):
        sentence = "This sentence is exactly fifty characters long ok."
        text = " ".join([sentence] * 6)
        chunks = chunk_text(text, size=120, overlap=0)
        self.assertTrue(all(c.endswith("ok.") for c in chunks), chunks)

    def test_overlap_repeats_end_of_previous_chunk(self):
        chunks = chunk_text(self.long_text(), size=300, overlap=80)
        for previous, current in zip(chunks, chunks[1:]):
            first_words = " ".join(current.split()[:3])
            self.assertIn(first_words, previous)

    def test_overlap_starts_on_a_word_boundary(self):
        text = self.long_text()
        chunks = chunk_text(text, size=300, overlap=80)
        original = set(words(text))
        for chunk in chunks[1:]:
            self.assertIn(chunk.split()[0], original)

    def test_one_enormous_word_is_hard_split(self):
        url = "https://example.org/" + "x" * 250
        chunks = chunk_text(url, size=100, overlap=0)
        self.assertEqual("".join(chunks), url)
        self.assertTrue(all(len(c) <= 100 for c in chunks))

    def test_invalid_settings_are_rejected(self):
        for size, overlap in ((0, 0), (-5, 0), (100, 100), (100, -1)):
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                chunk_text("text", size=size, overlap=overlap)


class PreprocessTests(SimpleTestCase):
    def test_cleans_then_chunks(self):
        chunks = preprocess("Skip to main content\n\nTea &amp; talk every Friday at noon in the garden room.")
        self.assertEqual(chunks, ["Tea & talk every Friday at noon in the garden room."])

    def test_nothing_useful_gives_no_chunks(self):
        self.assertEqual(preprocess("Menu\n© 2026 Example\n---"), [])

    def test_sample_page_with_custom_size(self):
        raw = (SAMPLE_DATA / "messy_page.txt").read_text(encoding="utf-8")
        chunks = preprocess(raw, size=300, overlap=60)
        self.assertEqual(len(chunks), 4)
        self.assertTrue(all(len(c) <= 300 for c in chunks))


class PreviewCommandTests(SimpleTestCase):
    def run_command(self, *args):
        out = io.StringIO()
        call_command("preview_preprocess", *args, stdout=out)
        return out.getvalue()

    def test_preview_sample_page(self):
        output = self.run_command(str(SAMPLE_DATA / "messy_page.txt"), "--size", "300", "--overlap", "60")
        self.assertIn("Cleaned text", output)
        self.assertIn("4 chunk(s), size 300, overlap 60", output)
        self.assertNotIn("Skip to main content", output)

    def test_missing_file(self):
        with self.assertRaisesMessage(CommandError, "File not found"):
            self.run_command("nope.txt")

    def test_bad_chunk_settings(self):
        with self.assertRaisesMessage(CommandError, "overlap must be"):
            self.run_command(str(SAMPLE_DATA / "messy_page.txt"), "--size", "100", "--overlap", "100")
