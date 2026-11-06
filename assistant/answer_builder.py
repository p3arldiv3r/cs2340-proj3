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

def build_answer(question, retrieved, template):
    if not retrieved:
        return Answer("I couldn't find an answer in our sources. Try different words or ask another question about social wellness.")
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
