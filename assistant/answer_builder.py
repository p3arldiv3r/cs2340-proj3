"""Evidence-only answers with intent-specific structure and checkable citations."""
import re
from dataclasses import dataclass
from knowledge.retrieval import terms


@dataclass(frozen=True)
class Citation:
    number: int
    document_id: int
    title: str
    url: str
    external_id: str
    excerpt: str


@dataclass(frozen=True)
class Recommendation:
    title: str
    description: str
    tags: tuple
    source_number: int


@dataclass(frozen=True)
class Answer:
    text: str
    sources: tuple = ()
    intent: str = 'factual'
    recommendations: tuple = ()


NO_ANSWER = "I couldn't find an answer in our sources."
INSTRUCTOR_QUESTION = re.compile(
    r"^who\s+(?:teaches|leads|instructs)\s+(.+?)[?!.]*$", re.IGNORECASE,
)


def _citation(document, number, excerpt):
    return Citation(
        number=number,
        document_id=document.pk,
        title=document.title,
        url=document.public_url,
        external_id=document.external_id,
        excerpt=excerpt,
    )


def _best_sentences(question, text, count):
    """Select relevant extractive sentences without adding unsupported claims."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n\n', text) if s.strip()]
    if not sentences:
        return ''
    query = set(terms(question))
    ranked = sorted(
        range(len(sentences)),
        key=lambda i: (-len(query & set(terms(sentences[i]))), i),
    )[:count]
    return ' '.join(sentences[i] for i in sorted(ranked))


def answer_instructor_question(activity_name, retrieved):
    """Answer from a matching activity's instructor metadata, not a guess."""
    for passage in retrieved:
        document = passage.chunk.document
        if document.title.strip().casefold() != activity_name.casefold():
            continue
        instructor = document.metadata.get('instructor')
        if isinstance(instructor, str) and instructor.strip():
            instructor = instructor.strip()
            return Answer(
                f'{document.title} is taught by {instructor}. [1]',
                (_citation(document, 1, f'Instructor: {instructor}'),),
            )
    return Answer("I couldn't find who teaches that activity in our sources.")



def _metadata_answer(question, retrieved):
    """Answer a named activity's simple factual fields, without guessing.

    Structured fields are more reliable than picking unrelated description
    sentences when a user asks whether an activity is free or online.
    """
    query = question.casefold()
    for passage in retrieved:
        document = passage.chunk.document
        if document.title.casefold() not in query:
            continue
        metadata = document.metadata
        fact = excerpt = None
        if re.search(r'\b(free|cost|price|fee|how much)\b', query) and metadata.get('cost'):
            cost = str(metadata['cost'])
            if re.search(r'\bfree\b', query) and cost.casefold() != 'free':
                fact = f'No. {document.title} costs {cost}.'
            elif cost.casefold() == 'free':
                fact = f'{document.title} is free.'
            else:
                fact = f'{document.title} costs {cost}.'
            excerpt = f'Cost: {cost}'
        elif re.search(r'\b(online|in person|virtual|format)\b', query) and metadata.get('format'):
            format_value = str(metadata['format'])
            fact = f'{document.title} is listed as {format_value.lower()}.'
            excerpt = f'Format: {format_value}'
        elif re.search(r'\b(morning|afternoon|evening|time of day)\b', query) and metadata.get('time_of_day'):
            time_value = str(metadata['time_of_day'])
            fact = f'{document.title} is listed for the {time_value.lower()}.'
            excerpt = f'Time of day: {time_value}'
        if fact:
            return Answer(f'{fact} [1]', (_citation(document, 1, excerpt),))
    return None


def _schedule_answer(question, retrieved):
    """Answer meeting-time questions using the actual schedule sentence.

    Markdown headings can score highly for a named group while omitting the
    meeting time. Prefer a complete schedule sentence from the matched source.
    """
    if not re.search(r"\b(?:when|what time|what day)\b", question, re.I):
        return None
    if not re.search(r"\b(?:meet|meets|meeting|start|starts|happen|held)\b", question, re.I):
        return None

    normalized_question = " ".join(question.casefold().split())
    for passage in retrieved:
        document = passage.chunk.document
        # Markdown titles may have a descriptive subtitle after a colon.
        activity_name = document.title.split(":", 1)[0].strip()
        if activity_name.casefold() not in normalized_question:
            continue
        # A line-wrapped sentence is still one sentence. Use the full original
        # document to avoid losing the time to a heading or paragraph break.
        text = " ".join(
            line.strip() for line in document.text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if not re.search(r"\b(?:meets?|takes place|held|scheduled)\b", sentence, re.I):
                continue
            if not re.search(r"\b(?:\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", sentence, re.I):
                continue
            return Answer(
                f"{sentence.strip()} [1]",
                (_citation(document, 1, sentence.strip()),),
                intent='factual',
            )
    return None


def _metadata_facts(document):
    """Present verified activity details without technical field names."""
    return ' · '.join(
        str(document.metadata[key])
        for key in ('format', 'time_of_day', 'cost')
        if document.metadata.get(key)
    )


def _is_activity(document):
    """Cards only for curated program records; articles/FAQs remain plain text."""
    return any(key in document.metadata for key in ('format', 'time_of_day', 'cost'))


def _recommendation_tags(document):
    return tuple(
        str(document.metadata[key])
        for key in ('format', 'time_of_day', 'cost')
        if document.metadata.get(key)
    )


def build_answer(question, retrieved, plan):
    """Apply the selected plan to the same grounded retrieval results.

    Factual: one short extract. Explanation: up to two richer extracts.
    Recommendation: up to two compact program cards, if program data exists.
    All answers cite *only* the documents used in the displayed response.
    """
    instructor_question = INSTRUCTOR_QUESTION.fullmatch(question.strip())
    if instructor_question:
        return answer_instructor_question(instructor_question.group(1).strip(), retrieved)

    if not retrieved:
        return Answer(NO_ANSWER + ' Try asking about an activity or group.', intent=plan.intent)

    if plan.intent == 'factual':
        schedule = _schedule_answer(question, retrieved)
        if schedule is not None:
            return schedule
        direct_fact = _metadata_answer(question, retrieved)
        if direct_fact is not None:
            return direct_fact

    # A recommendation must not turn an FAQ or a research article into an
    # "activity". If no curated activities match, present the evidence as text.
    if plan.intent == 'recommendation':
        activity_passages = [p for p in retrieved if _is_activity(p.chunk.document)]
        if activity_passages:
            seen, citations, recommendations, lines = set(), [], [], []
            for passage in activity_passages:
                document = passage.chunk.document
                if document.pk in seen:
                    continue
                seen.add(document.pk)
                excerpt = _best_sentences(question, passage.chunk.text, 1)
                if not excerpt:
                    continue
                number = len(citations) + 1
                citations.append(_citation(document, number, excerpt))
                tags = _recommendation_tags(document)
                recommendations.append(Recommendation(document.title, excerpt, tags, number))
                details = '; '.join(tags)
                lines.append(f'{document.title} [{number}]\n{excerpt}' + (f'\n{details}' if details else ''))
                if len(citations) >= plan.max_sources:
                    break
            if recommendations:
                return Answer(
                    plan.introduction + '\n\n' + '\n\n'.join(lines),
                    tuple(citations), plan.intent, tuple(recommendations),
                )

    seen, citations, sections = set(), [], []
    for passage in retrieved:
        document = passage.chunk.document
        if document.pk in seen:
            continue
        seen.add(document.pk)
        excerpt = _best_sentences(question, passage.chunk.text, plan.sentences_per_source)
        if not excerpt:
            continue
        number = len(citations) + 1
        citations.append(_citation(document, number, excerpt))
        text = f'{document.title} [{number}]\n{excerpt}'
        if plan.intent == 'explanation':
            metadata = _metadata_facts(document)
            if metadata:
                text += '\n' + metadata
        sections.append(text)
        if len(citations) >= plan.max_sources:
            break

    if not sections:
        return Answer(NO_ANSWER + ' Try asking about an activity or group.', intent=plan.intent)
    return Answer(plan.introduction + '\n\n' + '\n\n'.join(sections), tuple(citations), plan.intent)
