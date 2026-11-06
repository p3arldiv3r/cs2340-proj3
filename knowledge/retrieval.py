"""Deterministic lexical retrieval for a small curated corpus."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from .models import Chunk

STOP_WORDS = set('a an the is are was were be do does can could would should i me my you your we our to of for in on at and or with about what which how why when where please tell find some any information'.split())
SYNONYMS = {'friends': 'social', 'friend': 'social', 'friendship': 'social', 'lonely': 'loneliness', 'activities': 'activity', 'programs': 'program', 'groups': 'group', 'books': 'book', 'costs': 'cost'}
SYNONYMS.update({'connection': 'social', 'connections': 'social', 'connected': 'social',
                 'socially': 'social', 'isolation': 'loneliness', 'isolated': 'loneliness'})

def terms(text):
    return [SYNONYMS.get(w, w) for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in STOP_WORDS]

@dataclass(frozen=True)
class Passage:
    chunk: Chunk
    score: float

def retrieve(question, top_k=4):
    query = set(terms(question))
    if not query or top_k <= 0:
        return []
    chunks = list(Chunk.objects.select_related('document__source').all())
    corpus = [terms(c.document.title + ' ' + c.text + ' ' + ' '.join(str(v) for v in c.document.metadata.values())) for c in chunks]
    frequencies = Counter(w for words in corpus for w in set(words))
    ranked = []
    for chunk, words in zip(chunks, corpus):
        metadata = chunk.document.metadata
        # Respect explicit program constraints; don't recommend a paid or
        # in-person record just because another query word matched.
        constraints = {
            'format': [('online', 'online'), ('in person', 'in person')],
            'time_of_day': [(v, v) for v in ('morning', 'afternoon', 'evening')],
            'cost': [('free', 'free')],
        }
        incompatible = any(
            re.search(r'\b' + re.escape(phrase) + r'\b', question.lower())
            and key in metadata and str(metadata[key]).lower() != expected
            for key, choices in constraints.items() for phrase, expected in choices
        )
        if incompatible:
            continue
        counts = Counter(words)
        matched = query & counts.keys()
        if not matched or len(matched) / len(query) < 0.3:
            continue
        score = sum(math.log(1 + len(chunks) / frequencies[w]) * counts[w] / (counts[w] + 1) for w in matched)
        score *= len(matched) / len(query)
        ranked.append(Passage(chunk, score))
    return sorted(ranked, key=lambda p: (-p.score, p.chunk.pk))[:top_k]
