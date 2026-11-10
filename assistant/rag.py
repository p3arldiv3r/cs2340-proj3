"""Stable application boundary for web UI and evaluation."""
from knowledge.retrieval import retrieve
from .prompts import select_prompt
from .answer_builder import build_answer


def answer_question(question, user=None):
    plan = select_prompt(question)
    return build_answer(question, retrieve(question), plan)
