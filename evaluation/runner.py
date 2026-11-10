"""Compare the real assistant's responses against known, source-backed cases."""
from django.db import transaction

from assistant.rag import answer_question
from knowledge.models import Chunk, Document

from .cases import CASES
from .models import EvaluationResult, EvaluationRun


@transaction.atomic
def run_evaluation():
    """Save a complete run. Phrase matches alone do not count without citations.

    Uses the same answer_question boundary as normal chat. Only expected
    factual claims and cited source records are checked; this is a transparent
    deterministic check, not a semantic or clinical quality assessment.
    """
    if not Chunk.objects.exists():
        raise ValueError(
            "The knowledge base is empty. Load the sample files before running an evaluation."
        )

    # Warn rather than report a misleading low score when only part of the
    # sample dataset has been ingested.
    required_ids = {case.expected_source_id for case in CASES if case.expected_source_id}
    present_ids = set(Document.objects.filter(external_id__in=required_ids).values_list("external_id", flat=True))
    missing = required_ids - present_ids
    if missing:
        raise ValueError(
            "Load the sample evaluation sources first. Missing record IDs: " + ", ".join(sorted(missing))
        )

    run = EvaluationRun.objects.create(total=len(CASES))
    passed = 0
    for position, case in enumerate(CASES, 1):
        actual = ""
        source_ids = []
        feedback = []
        success = False
        try:
            answer = answer_question(case.question)
            actual = answer.text
            source_ids = list(dict.fromkeys(source.external_id for source in answer.sources))
            missing_phrases = [phrase for phrase in case.expected_phrases if phrase.casefold() not in actual.casefold()]
            if missing_phrases:
                feedback.append("Missing expected information: " + ", ".join(missing_phrases))
            if case.expects_no_answer:
                if source_ids:
                    feedback.append("Expected no cited source, but the answer cited a document.")
            elif case.expected_source_id not in source_ids:
                feedback.append("Expected source was not cited: " + case.expected_source_id)
            success = not feedback
        except Exception as exc:
            # Isolate a failed check so that staff can inspect it and the other
            # checks still run. Do not store tracebacks or arbitrary secrets.
            actual = "The assistant could not answer this test question."
            feedback.append("Assistant error: " + type(exc).__name__)

        EvaluationResult.objects.create(
            run=run,
            position=position,
            question=case.question,
            expected=case.expected,
            actual=actual,
            source_ids=source_ids,
            passed=success,
            feedback="; ".join(feedback),
        )
        passed += success

    run.passed = passed
    run.save(update_fields=("passed",))
    return run
