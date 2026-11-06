# Wellness assistant (Project 3)

A Django web assistant for social wellness information and activities for older adults. Answers are extracted from a curated knowledge base and include checkable source passages. No language model, paid API, or embeddings are required.

## Run locally

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py ingest upload sample_data/programs.json
.venv/Scripts/python manage.py ingest upload sample_data/book_circle.md
.venv/Scripts/python manage.py ingest upload sample_data/faq.txt
.venv/Scripts/python manage.py runserver
```

Open http://127.0.0.1:8000/assistant/. Try “What happens at Chair Yoga?” or “Find free online morning activities”. Sample activities are fictional demonstration records; load your reviewed topic sources for real use.

## How it works

```text
URL/file -> ingestion -> RawDocument -> preprocessing -> Source/Document/Chunk storage
Question -> intent/template -> ranked retrieval -> extractive answer + cited evidence
```

- `knowledge/ingestion/`: web pages, TXT, Markdown, CSV, JSON, and saved HTML.
- `knowledge/preprocessing.py`: cleaning, usefulness checks, content fingerprints, and overlapping chunks.
- `knowledge/pipeline.py`: atomic per-source replacement; the ingest command persists data.
- `knowledge/retrieval.py`: small-corpus lexical ranking, synonyms, and supported metadata constraints.
- `assistant/rag.py`: application entry point.
- `assistant/answer_builder.py`: structured Answer/Citation results; separate from the web UI for a future LLM upgrade.
- `assistant/views.py` and templates: public question form, answers, expandable evidence and original-source links.
- `core/` and shared templates: responsive Garden home, activities, help, and staff layouts; browser-local text size and contrast controls.
- Every application page includes a bottom-right assistant launcher. Its native dialog uses the same chat component and CSRF-protected `/assistant/ask/` service as the full-page assistant. Escape/Close returns focus to the launcher; mobile uses an expanded panel above the page. The launcher links to the full-page assistant when JavaScript is unavailable.
- `accounts/`: custom Django user. Chat does not require login or save conversation history.
- `evaluation/`, `monitoring/`: future work; pages remain staff-only placeholders.

Answers quote source text rather than synthesize new facts. Retrieval may miss paraphrases or misinterpret complex queries. Follow-up questions do not use conversation memory. Source documents and chunks are managed through the CLI and Django admin; the knowledge management page remains a placeholder.

## Add data

```sh
python manage.py ingest upload path/to/article.html
python manage.py ingest web https://example.org/article
```

Repeated ingestion of the same method/location replaces that source's documents. Failed fetches or writes preserve the existing source data. CSV/JSON records need a text/description/body/content field; other fields become metadata. See [ingestion](docs/testing/ingestion.md) and [preprocessing](docs/testing/preprocessing.md) documentation.

## Verify

```sh
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Hosting

See [deployment instructions](docs/deployment.md) for PythonAnywhere or another WSGI host, production settings, persistent SQLite, static assets, and public-URL acceptance checks. A real hosting account and deployment are required to make the app publicly accessible.

The accessible “Garden” visual direction is described in [DESIGN.md](DESIGN.md); it includes future product features beyond the implemented chatbot.
