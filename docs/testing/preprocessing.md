# Testing: data cleaning and preprocessing

**Story:** As a Developer, I want to clean and preprocess data before
ingestion, so retrieval results are accurate and relevant.

**Branch:** `preprocessing`

## What was built

`knowledge/preprocessing.py`: plain functions that take text in and give text
out. They have no database and no dependencies.

| Function | What it does |
|---|---|
| `clean_text(text)` | Makes text consistent to search and safe to quote (details below) |
| `is_useful(text, min_chars=40)` | False for documents with too little real content to store |
| `content_hash(text)` | Fingerprint for spotting duplicates; ignores case, spacing and boilerplate |
| `chunk_text(text, size=800, overlap=120)` | Splits cleaned text into chunks of at most `size` characters |
| `preprocess(text, size, overlap)` | All of the above in one call; returns `[]` if nothing useful is left |

### What `clean_text` does

1. **HTML leftovers:** decodes entities (`&amp;` → `&`) and strips leftover tags.
2. **Unicode:** normalizes it (NFKC): non-breaking spaces become spaces,
   ligatures (`ﬁ`) become letters, full-width letters become normal ones.
3. **Punctuation:** curly quotes and hyphen/en-dash variants become plain
   ASCII, so "library’s" matches "library's". Em dashes are kept.
4. **Invisible characters:** removes zero-width spaces, soft hyphens,
   byte-order marks and control characters.
5. **Whitespace:** collapses runs of spaces and tabs, trims every line, and
   converts Windows line endings.
6. **Boilerplate:** drops short boilerplate lines:
   - menu-style phrases, but only when they're the whole line: "Skip to main
     content", "Menu", "Share this page", "Follow us on …", "Privacy Policy"
   - lines starting with © or "Copyright 2026"
   - cookie banners and "All rights reserved" lines

   Real sentences that happen to use those words are kept, e.g. "Subscribe to
   updates at the front desk."
7. **Dividers:** drops lines with no letters or digits (`----`, `| | |`).
8. **Repeats:** drops a line that repeats the previous non-blank line (scraped
   pages often repeat headings).
9. **Paragraphs:** keeps paragraph breaks as exactly one blank line.

Running `clean_text` twice gives the same result as running it once.

### How `chunk_text` splits

It splits between **paragraphs** first. A paragraph longer than `size` is split
between **sentences**, and a sentence longer than `size` between **words**.
Words are never cut, except a single "word" longer than `size`, such as a very
long URL.

Small paragraphs are packed together up to `size`. Each chunk after the first
starts with up to `overlap` characters from the end of the previous chunk,
starting at a word boundary. That way a fact split across a boundary can still
be found.

### Using it in your story

```python
from knowledge.preprocessing import clean_text, content_hash, is_useful, chunk_text, preprocess

# Simple:
chunks = preprocess(raw_text)            # [] means skip this document

# Storing documents (dataset story):
cleaned = clean_text(raw_text)
if is_useful(cleaned) and not Document.objects.filter(content_hash=content_hash(cleaned)).exists():
    ...  # save cleaned, then save each of chunk_text(cleaned)
```

It works on any string. With the ingestion branch merged, pass it
`RawDocument.text` (and `clean_text(RawDocument.title)` for titles).

## 1. Automated tests

From the repo root:

```
python manage.py test knowledge.test_preprocessing
```

Expected: `Ran 43 tests ... OK`.

They cover:
- **Each cleaning rule above:** includes checks that real sentences with
  boilerplate-looking words are kept, and that long lines are never treated
  as boilerplate.
- **Idempotence:** cleaning twice changes nothing.
- **`is_useful`:** too-short documents, boilerplate-only documents, and
  documents with no letters.
- **`content_hash`:** spacing, case and boilerplate don't change the hash;
  different text does.
- **Chunk size:** no chunk is ever longer than `size`, across several
  size/overlap settings.
- **No words lost or cut:** with no overlap, the chunks rejoin to exactly the
  original words.
- **Split points:** paragraph boundaries preferred, small paragraphs packed,
  long paragraphs split at sentences, a huge "word" hard-split.
- **Overlap:** repeats the end of the previous chunk and starts on a word
  boundary.
- **Bad settings:** invalid size/overlap raises `ValueError`.
- **The `preview_preprocess` command.**

## 2. Manual check (about 3 minutes)

`preview_preprocess` shows what preprocessing does to a file. It saves nothing.

```
python manage.py preview_preprocess sample_data/messy_page.txt --size 300 --overlap 60
```

`sample_data/messy_page.txt` is a fictional scraped page full of junk. Under
**Cleaned text**, check:

- [ ] It starts with `Tech Help Hour & Q&A`, shown once (the raw file has it
      twice, once as `&amp;`).
- [ ] None of these are left: "Skip to main content", "Accept all cookies",
      "Menu", the `----------` and `| | |` lines, "Share this page",
      "Follow us on Facebook", or the `© 2026 … All rights reserved.` line.
- [ ] `one-on-one` and `library's` use plain hyphens and apostrophes, and
      `1:00 to 3:00 PM` has normal spaces.
- [ ] The summary line says about `1050 chars before, 844 after`.

Under **4 chunk(s), size 300, overlap 60**, check:

- [ ] Every chunk is 300 characters or fewer (each chunk's header shows its length).
- [ ] No chunk starts or ends in the middle of a word.
- [ ] Chunks 2–4 each start with words from the end of the chunk before them.

Try it on your own data too: any `.txt` file works. Change `--size` and
`--overlap` to see the effect. `--overlap` must be smaller than `--size`, or
you get a clear error.

## Done checklist

- [ ] `python manage.py test knowledge.test_preprocessing` passes
- [ ] Manual check: cleaned text has no boilerplate/junk, and chunks respect the size
- [ ] Other stories can call `preprocess()` / `clean_text()` / `chunk_text()` / `content_hash()`

## Known limits / follow-ups

- **Size is in characters, not tokens or words.** The default of 800 is a
  starting point; tune it once retrieval is built and accuracy can be measured
  (evaluation story).
- **English-centric boilerplate list.** It catches common English website
  chrome only. Add patterns to `_BOILERPLATE_LINE_RE` / `_BOILERPLATE_START_RE`
  as real scraped data shows new junk, with a test for each.
- **No spelling fixes, stemming or stopword removal.** Those belong to
  retrieval, which needs the original text to quote sources accurately.
