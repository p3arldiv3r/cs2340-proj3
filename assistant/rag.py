"""Stable application boundary for web UI and evaluation."""
from knowledge.retrieval import retrieve
from .prompts import classify_intent, choose_template
from .answer_builder import build_answer

def answer_question(question, user=None):
    return build_answer(question, retrieve(question), choose_template(classify_intent(question)))
