"""Builds the reply from the retrieved passages, with no language model.

e.g. pick the most relevant sentences from the top passages, drop them into
the response template for the question type (prompts.py), and cite which
documents they came from.
"""


def build_answer(question, retrieved, template):
    raise NotImplementedError
