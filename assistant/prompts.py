"""TODO (Developer: dynamically select or construct prompts based on the type
of user question, e.g. factual lookup vs. explanation vs. creative).

With no language model, a "prompt" here is a response template per question
type (e.g. a factual lookup gives one short quoted answer; a recommendation
lists a few options).
"""


def classify_intent(question):
    raise NotImplementedError


def choose_template(intent):
    raise NotImplementedError
