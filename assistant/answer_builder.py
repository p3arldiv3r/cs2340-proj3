"""Extractive generation; citations identify only evidence used in the reply."""
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
class Answer:
    text: str
    sources: tuple = ()

NO_ANSWER = "I couldn't find an answer in our sources."

INSTRUCTOR_QUESTION = re.compile(
    r"^who\s+(?:teaches|leads|instructs)\s+(.+?)[?!.]*$",
    re.IGNORECASE,
)


def answer_instructor_question(activity_name, retrieved):
    """Answer from the named activity's instructor field."""
    for passage in retrieved:
        document = passage.chunk.document
        if document.title.strip().casefold() != activity_name.casefold():
            continue

        instructor = document.metadata.get("instructor")
        if isinstance(instructor, str) and instructor.strip():
            instructor = instructor.strip()
            return Answer(
                f"{document.title} is taught by {instructor}. [1]",
                (Citation(
                    number=1,
                    document_id=document.pk,
                    title=document.title,
                    url=document.public_url,
                    external_id=document.external_id,
                    excerpt=f"Instructor: {instructor}",
                ),),
            )

    return Answer("I couldn't find who teaches that activity in our sources.")

def build_answer(question, retrieved, template):
    instructor_question = INSTRUCTOR_QUESTION.fullmatch(question.strip())
    if instructor_question:
        return answer_instructor_question(
            instructor_question.group(1).strip(), retrieved
        )

    if not retrieved:
        return Answer(
            NO_ANSWER
            + " Try different words or ask another question about social wellness."
        )
    citations, sections, seen = [], [], set()
    query = set(terms(question))
    for passage in retrieved:
        document = passage.chunk.document
        if document.pk in seen:
            continue
        seen.add(document.pk)
        sentences = re.split(r'(?<=[.!?])\s+|\n\n', passage.chunk.text)
        best = sorted(range(len(sentences)), key=lambda i: (-len(query & set(terms(sentences[i]))), i))[:2]
        excerpt = ' '.join(sentences[i] for i in sorted(best))
        number = len(citations) + 1
        citations.append(Citation(number, document.pk, document.title, document.public_url, document.external_id, excerpt))
        metadata = '; '.join(f'{key}: {value}' for key, value in document.metadata.items() if key in ('format', 'time_of_day', 'cost'))
        sections.append(f'{document.title} [{number}]\n{excerpt}' + (f'\n{metadata}' if metadata else ''))
    return Answer(template + '\n\n' + '\n\n'.join(sections), tuple(citations))
