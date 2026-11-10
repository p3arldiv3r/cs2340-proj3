"""Known-answer checks for the curated sample knowledge base.

These are acceptance checks, not training data. Update them when the curated
sample corpus is deliberately changed. Every positive case requires both a
supported answer phrase and the correct source record.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationCase:
    question: str
    expected: str
    expected_phrases: tuple[str, ...]
    expected_source_id: str = ""
    expects_no_answer: bool = False


CASES = (
    EvaluationCase("Who teaches Chair Yoga?", "Jordan Lee", ("Jordan Lee",), "prog-101"),
    EvaluationCase("Is Chair Yoga free?", "Chair Yoga is free", ("Chair Yoga is free",), "prog-101"),
    EvaluationCase("Is Chair Yoga online?", "Online", ("online",), "prog-101"),
    EvaluationCase("How much does Watercolor Basics cost?", "$5 per class", ("$5 per class",), "prog-102"),
    EvaluationCase("Is Coffee and Conversation in person?", "In person", ("in person",), "prog-103"),
    EvaluationCase(
        "When does the Afternoon Book Circle meet?",
        "First Thursday of every month, 3:00 to 4:00 PM Eastern Time",
        ("first Thursday", "3:00", "4:00"),
        "book_circle.md",
    ),
    EvaluationCase(
        "Find free online morning activities",
        "Recommend Chair Yoga from prog-101",
        ("Chair Yoga",),
        "prog-101",
    ),
    EvaluationCase(
        "What is quantum astrophysics?",
        "Say that no supporting answer was found",
        ("couldn't find an answer",),
        expects_no_answer=True,
    ),
)
