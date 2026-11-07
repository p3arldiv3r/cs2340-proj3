# Testing: administrator monitoring, usage logs, and knowledge base reload

**Stories:**

1. As an Administrator, I want to monitor system performance (latency,
   failures), so the chatbot meets responsiveness requirements.
2. As an Administrator, I want to manually clear or reload the chatbot's
   knowledge base so I can recover from incorrect or outdated data.
3. As an Administrator, I want to view basic usage logs (e.g., number of
   queries, timestamps, response times) so I can understand how the chatbot is
   being used.

**Branch:** `admin-tools`

## What was built

| Piece | What it does |
|---|---|
| `monitoring.models.QueryLog` | One row per question: time, channel (page or popup), response time in ms, success, number of cited sources, error class name. The question text is never stored. |
| `monitoring.services.timed_answer` | Wraps `answer_question` in both chat views. Times the call and writes a `QueryLog`. If the log write fails, the chat still answers. |
| `monitoring.services.summarize(days)` | Totals, failure rate, unanswered count, average/median/95th-percentile/max latency, count over target, per-channel and per-day counts, recent rows. |
| `/monitoring/` | Staff dashboard: period chooser (1, 7, 30 days), target status banner, performance and usage cards, per-day and recent-question tables. |
| `/knowledge/` | Staff page: source list, document and passage counts, **Reload** and **Clear** buttons. |
| Django admin | Read-only `Query logs` list with filters and date drill-down. |

The response-time target is `ASSISTANT_LATENCY_TARGET_MS` (environment
variable, default `2000`). The target is met when the 95th-percentile latency
is at or under it.

**Clear** removes all documents and passages. It requires a confirmation box.
By default it keeps the source list, so **Reload** can fetch it again. Tick
"Also remove the source list" to forget the sources too.

**Reload** re-fetches every source in one transaction. If any source fails,
every existing document is kept.

## Automated tests

```sh
python manage.py test monitoring knowledge.test_management
```

| Story | Test |
|---|---|
| 1, 3 | Page and popup questions are logged with latency, timestamp, channel, source count |
| 1 | Failures are logged with error type only; private error text is not stored |
| 1 | A broken log write does not break the chat |
| 3 | Question text is not stored; invalid questions are not logged |
| 1 | Percentiles, average, max, failure rate, over-target count, target status |
| 3 | Period filter, per-day counts, newest-first recent list, recent limit |
| 1, 3 | Dashboard is staff-only, shows empty state, metrics, slow-response flag; bad `days` values fall back to 7 |
| 3 | Admin query log is read-only |
| 2 | Manage page is staff-only, CSRF-protected, shows counts and sources |
| 2 | Clear needs confirmation; clears documents and keeps sources, or forgets sources too |
| 2 | Reload restores after clear and replaces outdated or hand-edited documents |
| 2 | A failed reload keeps every existing document; reload with no sources shows a message |
| 2 | Unknown actions and GET requests change nothing |

## Manual check

1. Start the app and create a staff account (see README).
2. Ask a few questions at `/assistant/` and in the popup, including one with no
   match, such as "quantum astrophysics".
3. Open `/monitoring/`. The question count, response times, and recent rows
   match what you asked. "No matching source" counts the unmatched question.
4. Set `ASSISTANT_LATENCY_TARGET_MS=1` and restart. The banner says "Slower
   than target".
5. Open `/knowledge/`. Tick the confirmation box and click **Clear knowledge
   base**. Documents drop to 0, and the assistant says it couldn't find an
   answer.
6. Click **Reload knowledge base**. Document counts return and answers work
   again.
