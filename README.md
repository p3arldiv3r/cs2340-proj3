# Wellness assistant (Project 3)

RAG chatbot for a social wellness platform for older adults. UI follows
[DESIGN.md](DESIGN.md) ("Garden" design system; tokens are in
`core/static/core/garden.css`).

## Run locally

```
cd wellness
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Where each story goes

Every file below is a stub (`raise NotImplementedError` or a placeholder page)
with a TODO naming its story.

| Story | App / file |
|---|---|
| End User: access the chatbot through a hosted web app | `core/`, `wellness/settings.py` (env vars for hosting) |
| End User: ask natural language questions | `assistant/views.py`, `assistant/rag.py` |
| End User: responses grounded in the dataset | `assistant/rag.py`, `knowledge/retrieval.py`, `assistant/answer_builder.py` |
| End User: see which sources were used | `assistant/models.py`, `assistant/templates/assistant/chat.html` |
| Developer: define and update the dataset | `knowledge/models.py`, `knowledge/views.py` |
| Developer: ingest with 2+ distinct methods | `knowledge/ingestion/web.py` (web scraper), `knowledge/ingestion/upload.py` (our data files) |
| Developer: clean and preprocess data | `knowledge/preprocessing.py` |
| Developer: prompts chosen by question type | `assistant/prompts.py` (response template per question type) |
| Developer: test accuracy against known questions | `evaluation/` (`runner.py`) |
| Administrator: monitor latency and failures | `monitoring/` (`services.py`) |
| Administrator: clear or reload the knowledge base | `knowledge/pipeline.py`, `knowledge/views.py` |
| Administrator: view usage logs | `monitoring/models.py`, `monitoring/views.py` |

## How answers are built

No language model. The knowledge base is built from web scraping and data
files we provide. `knowledge/retrieval.py` finds the most relevant passages,
and `assistant/answer_builder.py` assembles the reply from them using the
template for the question type, citing its sources.
