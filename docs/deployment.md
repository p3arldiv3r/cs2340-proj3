# Hosting the wellness assistant

The app uses Django WSGI, SQLite, and server-rendered HTML. No API key or model service is required. Python 3.11+ is recommended.

## Local setup

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py ingest upload sample_data/programs.json
.venv/Scripts/python manage.py ingest upload sample_data/book_circle.md
.venv/Scripts/python manage.py ingest upload sample_data/faq.txt
.venv/Scripts/python manage.py runserver
```

Open http://127.0.0.1:8000/assistant/. Try “What happens at Chair Yoga?” or “Find free online morning activities”. Open Sources used to inspect the supporting passage and record ID. Sample program records are fictional demonstration data.

To load actual topic documents, use `python manage.py ingest upload path/to/article.html` or `python manage.py ingest web https://example.org/article`. Scraping and parsing are admin/CLI operations, never driven by public chat input. Repeating a source replaces its documents atomically. A fetch/processing failure preserves its existing records. Use the same source location when updating a file; moving it creates a separate source.

## Production environment

Set these variables in your hosting configuration (the app does not automatically load .env files):

* `WELLNESS_DEBUG=false`
* `WELLNESS_SECRET_KEY`: a long randomly generated secret, kept outside version control
* `WELLNESS_ALLOWED_HOSTS`: your hostname, e.g. `yourname.pythonanywhere.com`
* `WELLNESS_DATABASE_PATH`: absolute path to SQLite on persistent writable storage
* `WELLNESS_TRUST_PROXY=true` only if the host's reverse proxy strips client-supplied forwarded headers and reliably sets X-Forwarded-Proto

Deploy code and install requirements, then run:

```sh
python manage.py migrate
python manage.py ingest upload sample_data/programs.json
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Replace demo data with your selected, reviewed topic sources. Back up the database. Do not place SQLite on ephemeral storage; it contains the searchable knowledge base. This implementation targets a small corpus and low traffic, using one application instance. Larger deployments should move to a shared database and indexed retrieval.

### PythonAnywhere

Create a manually configured Python web app, configure its virtualenv and source directory, and edit its WSGI file to set the environment variables above before importing the application:

```python
import os
import sys

sys.path.insert(0, '/home/YOUR_USERNAME/cs2340-proj3')
# Set the production environment variables here or through your host's configuration.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wellness.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Enable HTTPS through the host, run the production commands from the source directory using the configured virtualenv, then reload the web app. WhiteNoise serves collected static assets. Use your host's HTTPS/proxy configuration to prevent redirect loops.

### Other WSGI hosts

The Procfile starts Waitress on the host-provided PORT. A TLS reverse proxy must serve the public HTTPS endpoint. Alternatively run `waitress-serve --listen=127.0.0.1:8000 wellness.wsgi:application` behind your own proxy. Do not use Django's development server for public hosting.

## Acceptance checks on the deployed URL

1. From another device, open the home page and follow Ask your assistant.
2. Submit a supported question; verify answer passages and expanded source details.
3. For web/saved-HTML sources, verify Read original opens the original document.
4. Ask an unrelated question; verify the no-match response.
5. Submit empty/overlong input; verify a readable error.
6. Confirm CSS loads over HTTPS and staff pages redirect anonymous visitors to login.

## Design and limitations

`knowledge.pipeline` stores ingested records as Source → Document → Chunk. Retrieval ranks lexical overlap with inverse document frequency and a small synonym map. Explicit supported program preferences exclude incompatible metadata. The answer builder extracts up to two sentences per cited document; it does not synthesize facts. Retrieval is heuristic and may miss paraphrases or misunderstand complex questions. It is not a general-purpose conversational model and does not resolve follow-up questions using history.

`assistant.rag.answer_question` is the application boundary. Both a future LLM builder and the current extractive builder should return `Answer(text, sources)`. Each citation keeps the document ID, record ID, title, safe public URL, and exact supporting excerpt. No question history is stored by this implementation. Hosts may still keep infrastructure logs; review those settings before deployment.

Run `python manage.py test` for ingestion, preprocessing, storage, retrieval, citations, form validation, CSRF, HTML escaping, and chat integration tests. The public-URL story still needs an actual hosting account and deployment to complete its anywhere-access acceptance check.
