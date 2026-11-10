"""Choose a grounded, intent-specific response plan for the extractive assistant.

The app does not call an LLM. These plans are *executable prompts*: the answer
builder uses their different rules to select evidence and format the response.
They can also be used as instructions if an LLM is added in the future.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PromptPlan:
    intent: str
    instruction: str
    introduction: str
    max_sources: int
    sentences_per_source: int


# These instructions are defined by the application, not by retrieved documents.
# All strategies use the same evidence-only grounding rule.
_GROUNDING = "Use only retrieved evidence; cite each source and never invent details. "
PLANS = {
    'factual': PromptPlan(
        'factual',
        _GROUNDING + 'Give the requested fact directly and briefly.',
        'Here is what I found:', 1, 1,
    ),
    'explanation': PromptPlan(
        'explanation',
        _GROUNDING + 'Explain simply, with a little context and clear language.',
        'Here is how it works:', 2, 2,
    ),
    'recommendation': PromptPlan(
        'recommendation',
        _GROUNDING + 'Show up to two matching activities with useful details.',
        'Here are some options:', 2, 1,
    ),
}

# Intent is chosen from the *question*, never from outside source text.
_EXPLANATION = re.compile(
    r'\b(?:how|why|explain|describe|walk me through|what happens|what can i expect|'
    r'help me (?:understand|use|join|navigate))\b', re.IGNORECASE
)
_RECOMMENDATION = re.compile(
    r'\b(?:recommend\w*|suggest\w*|find|looking for|ideas?|options?|'
    r'activities|programs|groups|classes|what can i (?:do|join|try))\b',
    re.IGNORECASE,
)
_FACT_LOOKUP = re.compile(r'\b(?:how much|how many|what time|how long)\b', re.IGNORECASE)


def classify_intent(question):
    """Identify what kind of answer the user needs; default to a fact lookup.

    Explanation questions win over generic topic words: "How do groups work?"
    is not a recommendation simply because it contains "groups".
    "How much does ... cost?" is a fact lookup, not an explanation.
    """
    question = (question or '').strip()
    if _FACT_LOOKUP.search(question):
        return 'factual'
    if _EXPLANATION.search(question):
        return 'explanation'
    if _RECOMMENDATION.search(question):
        return 'recommendation'
    return 'factual'


def select_prompt(question):
    """Return the response plan that is actually applied by the answer builder."""
    return PLANS[classify_intent(question)]


def choose_template(intent):
    """Compatibility helper for code that needs only a short introduction."""
    return PLANS.get(intent, PLANS['factual']).introduction
