"""Cleaning and chunking applied to every document before it is stored.

Story: "As a Developer, I want to clean and preprocess data before ingestion,
so retrieval results are accurate and relevant."

    from knowledge.preprocessing import preprocess
    chunks = preprocess(raw_text)          # [] if nothing useful is left

Or step by step: clean_text() -> is_useful() -> chunk_text(), and
content_hash() to spot duplicates. See docs/testing/preprocessing.md.
"""

import hashlib
import html
import re
import unicodedata


# Chunks are measured in characters. ~800 characters is a few short paragraphs:
# big enough to hold a whole answer, small enough to stay on one topic.
CHUNK_SIZE = 800
# Characters repeated from the end of one chunk at the start of the next, so a
# sentence that straddles a boundary can still be found.
CHUNK_OVERLAP = 120
# Cleaned documents shorter than this are treated as empty.
MIN_USEFUL_CHARS = 40

_TAG_RE = re.compile(r"<[^>]+>")
_SPACES_RE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
# Zero-width spaces/joiners, soft hyphens and byte-order marks.
_INVISIBLE_RE = re.compile("[­​‌‍⁠﻿]")
# Control characters other than newline and tab.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Curly quotes and hyphen/en-dash variants to plain ASCII, so "library's" and
# "one-on-one" match however they were typed. Em dashes are kept.
_PUNCTUATION = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "−": "-",
})

# Page chrome that scrapers and exports pick up. Only short lines are checked,
# so real sentences are kept.
_BOILERPLATE_MAX_CHARS = 120
# Menu-style phrases: dropped only when they are the whole line.
_BOILERPLATE_LINE_RE = re.compile(
    r"(skip to (main )?content|(accept|reject|manage) (all )?cookies|"
    r"subscribe( now)?|sign up for our newsletter|share( this( page| article)?)?|"
    r"follow us( on \w+)?|back to top|privacy policy|terms (of use|of service|and conditions)|"
    r"menu|search|print( this page)?|learn more|read more|view all|related (pages|links|articles)|"
    # Share buttons, as bare network names.
    r"facebook|twitter|x|linkedin|instagram|youtube|pinterest|email|syndicate|"
    # Page feedback widgets (found on the real CDC page). Bare "Yes" / "No"
    # answers are kept on purpose: in an FAQ they are the actual answer.
    r"was this (page|information) helpful\?|how would you rate this (page|information)\?|"
    r"thank you for your feedback|not helpful|very helpful|"
    # Research-article pages (PubMed Central and similar journal sites).
    r"author information|article notes|copyright and license information|pmc copyright notice|"
    r"find articles by .+|click here for additional data file.*)[.!:]*",
    re.IGNORECASE,
)
# Lines that are boilerplate from their first words: copyright notices and cookie banners.
_BOILERPLATE_START_RE = re.compile(
    r"(©|\(c\)|copyright\s*(©|\(c\))?\s*\d{4}|we use cookies|this (web)?site uses cookies)",
    re.IGNORECASE,
)


def _is_boilerplate(line):
    if len(line) > _BOILERPLATE_MAX_CHARS:
        return False
    return bool(
        _BOILERPLATE_LINE_RE.fullmatch(line)
        or _BOILERPLATE_START_RE.match(line)
        or "all rights reserved" in line.lower()
    )


# Link badges journal sites put after every citation.
_CITATION_LINK_RE = re.compile(
    r"\[(DOI|PubMed|Google Scholar|PMC free article|CrossRef|Free full text|Ref list)\]", re.IGNORECASE
)
# An email address, along with an "Email:" label in front of it.
_EMAIL_RE = re.compile(r"(\b(e-?mail|contact)\s*:\s*)?[\w.+-]+@[\w-]+(\.[\w-]+)+", re.IGNORECASE)
# Separators left dangling once an address is removed: "Min Liu, Email: x@y.org." -> "Min Liu."
_DANGLING_SEPARATOR_RE = re.compile(r"\s*[,;]\s*(?=[.;]?$)")

# A heading that starts the reference list of a research article.
_REFERENCES_HEADING_RE = re.compile(
    r"(references|bibliography|works cited|literature cited|reference list|citations):?", re.IGNORECASE
)
# Things nearly every citation line has and ordinary prose rarely does.
_CITATION_SIGNAL_RE = re.compile(
    r"\b(19|20)\d{2}\b|\bdoi\b|\bet al\b|\bvol\.|\bpp?\.\s*\d|\[(pubmed|google scholar|doi)\]", re.IGNORECASE
)
# Share of lines after the heading that must look like citations. Measured on
# the team's PMC articles: reference lists scored 0.56 and 0.95, article bodies
# never above 0.19.
_REFERENCES_MIN_SIGNAL = 0.4


def _drop_reference_list(lines):
    """Cut everything from the last "References" heading on, but only when
    what follows really looks like a citation list. Checking the content (not
    just the heading's position) keeps clean_text stable when run twice."""
    headings = [i for i, line in enumerate(lines) if _REFERENCES_HEADING_RE.fullmatch(line)]
    if not headings:
        return lines
    start = headings[-1]
    after = [line for line in lines[start + 1:] if line]
    if len(after) < 3:
        return lines
    signal = sum(bool(_CITATION_SIGNAL_RE.search(line)) for line in after) / len(after)
    return lines[:start] if signal >= _REFERENCES_MIN_SIGNAL else lines


def clean_text(text, remove_emails=True, drop_references=True):
    """Return text that is safe and consistent to search and quote.

    - decodes HTML entities (&amp; -> &) and strips any leftover tags
    - normalizes unicode (non-breaking spaces, ligatures, full-width letters),
      curly quotes and hyphens to plain ASCII, and Windows line endings
    - removes invisible and control characters
    - removes citation link badges ("[DOI] [PubMed] [Google Scholar]")
    - removes email addresses, with any "Email:" label (remove_emails=False keeps them)
    - collapses runs of spaces/tabs and trims every line
    - drops short boilerplate lines (cookie banners, "Skip to content", copyright,
      and research-article chrome like "Author information", "Find articles by ...")
    - drops lines with no letters or digits (dividers like "---" or "|")
    - drops a line that repeats the previous non-blank line
    - drops a research article's reference list (drop_references=False keeps it)
    - keeps paragraph breaks as a single blank line

    Running it twice gives the same result as running it once.
    """
    if not text:
        return ""
    text = html.unescape(str(text))
    text = _TAG_RE.sub(" ", text)
    text = unicodedata.normalize("NFKC", text).translate(_PUNCTUATION)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INVISIBLE_RE.sub("", text)
    text = _CONTROL_RE.sub("", text)
    text = _CITATION_LINK_RE.sub("", text)

    lines = []
    previous = None
    for line in text.split("\n"):
        if remove_emails and "@" in line:
            line = _DANGLING_SEPARATOR_RE.sub("", _EMAIL_RE.sub("", line))
        line = _SPACES_RE.sub(" ", line).strip()
        if line and (_is_boilerplate(line) or not any(c.isalnum() for c in line)):
            continue
        if line and line == previous:
            continue
        lines.append(line)
        if line:
            previous = line

    if drop_references:
        lines = _drop_reference_list(lines)
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()


def is_useful(text, min_chars=MIN_USEFUL_CHARS):
    """True if cleaned text has enough real content to be worth storing."""
    cleaned = clean_text(text)
    return len(cleaned) >= min_chars and any(c.isalpha() for c in cleaned)


def content_hash(text):
    """Fingerprint for spotting duplicate documents. Ignores case and
    whitespace differences, so a re-scraped page with new spacing still matches."""
    normalized = " ".join(clean_text(text).lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _split_long_paragraph(paragraph, size):
    """Break a paragraph longer than size into sentences, and any sentence
    still longer than size into word-wrapped pieces."""
    pieces = []
    for sentence in _SENTENCE_END_RE.split(paragraph):
        while len(sentence) > size:
            cut = sentence.rfind(" ", 0, size + 1)
            if cut <= 0:
                cut = size  # one enormous "word" (e.g. a URL): hard cut
            pieces.append(sentence[:cut].rstrip())
            sentence = sentence[cut:].lstrip()
        if sentence:
            pieces.append(sentence)
    return pieces


def _overlap_tail(chunk, overlap):
    """The last ~overlap characters of chunk, starting at a word boundary."""
    if overlap <= 0 or len(chunk) <= overlap:
        return ""
    tail = chunk[-overlap:]
    space = tail.find(" ")
    return tail[space + 1:] if space != -1 else ""


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into chunks of at most size characters.

    Splits between paragraphs when it can, then between sentences, then
    between words; it never cuts a word in half unless the word itself is
    longer than size. Each chunk after the first starts with up to overlap
    characters copied from the end of the previous chunk. Expects text that
    has already been through clean_text().
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be at least 0 and smaller than size")

    # (piece, starts_new_paragraph)
    pieces = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            pieces.append((paragraph, True))
        else:
            parts = _split_long_paragraph(paragraph, size)
            pieces.extend((part, i == 0) for i, part in enumerate(parts))

    chunks = []
    current = ""
    for piece, new_paragraph in pieces:
        joiner = "\n\n" if new_paragraph else " "
        if not current:
            current = piece
        elif len(current) + len(joiner) + len(piece) <= size:
            current += joiner + piece
        else:
            chunks.append(current)
            tail = _overlap_tail(current, overlap)
            if tail and len(tail) + len(joiner) + len(piece) <= size:
                current = tail + joiner + piece
            else:
                current = piece
    if current:
        chunks.append(current)
    return chunks


def preprocess(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """clean_text + is_useful + chunk_text in one call. Returns [] when the
    document has nothing worth keeping."""
    cleaned = clean_text(text)
    if not is_useful(cleaned):
        return []
    return chunk_text(cleaned, size=size, overlap=overlap)
