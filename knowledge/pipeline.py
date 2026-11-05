"""Stores ingested documents, and lets admins clear/reload the knowledge base.

TODO (Administrator: manually clear or reload the chatbot's knowledge base).
"""


def ingest_source(source):
    raise NotImplementedError


def clear_knowledge_base():
    raise NotImplementedError


def reload_knowledge_base():
    raise NotImplementedError
