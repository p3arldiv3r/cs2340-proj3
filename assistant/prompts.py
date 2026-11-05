"""TODO (Developer: dynamically select or construct prompts based on the type
of user question, e.g. factual lookup vs. explanation vs. creative)."""


def classify_intent(question):
    raise NotImplementedError


def build_prompt(question, retrieved, intent):
    raise NotImplementedError
