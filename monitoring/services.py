"""Record assistant queries and summarize performance and usage for staff."""
import logging
import math
import time
from datetime import timedelta
from django.conf import settings
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.utils import timezone
from .models import QueryLog

logger = logging.getLogger(__name__)


def latency_target_ms():
    return getattr(settings, 'ASSISTANT_LATENCY_TARGET_MS', 2000)


def timed_answer(answer_fn, question, channel, **kwargs):
    """Call answer_fn(question, **kwargs), log latency and outcome, and return
    its result. Exceptions are logged then re-raised for the view to handle."""
    start = time.perf_counter()
    try:
        answer = answer_fn(question, **kwargs)
    except Exception as exc:
        record(channel, start, succeeded=False, error_type=type(exc).__name__)
        raise
    record(channel, start, succeeded=True, source_count=len(answer.sources))
    return answer


def record(channel, start, **fields):
    latency_ms = round((time.perf_counter() - start) * 1000)
    try:
        QueryLog.objects.create(channel=channel, latency_ms=latency_ms, **fields)
    except Exception:
        # Monitoring must never break the chat itself.
        logger.exception('Could not record query log')


def percentile(values, fraction):
    """Nearest-rank percentile of an ascending list; None when empty."""
    if not values:
        return None
    return values[max(1, math.ceil(len(values) * fraction)) - 1]


def summarize(days=7, recent=50):
    since = timezone.now() - timedelta(days=days)
    logs = QueryLog.objects.filter(created_at__gte=since)
    latencies = sorted(logs.values_list('latency_ms', flat=True))
    total = len(latencies)
    failures = logs.filter(succeeded=False).count()
    unanswered = logs.filter(succeeded=True, source_count=0).count()
    target = latency_target_ms()
    slow = sum(latency > target for latency in latencies)
    p95 = percentile(latencies, 0.95)
    return {
        'days': days,
        'total': total,
        'failures': failures,
        'failure_rate': failures / total if total else 0,
        'unanswered': unanswered,
        'avg_ms': round(sum(latencies) / total) if total else None,
        'median_ms': percentile(latencies, 0.5),
        'p95_ms': p95,
        'max_ms': latencies[-1] if latencies else None,
        'target_ms': target,
        'slow': slow,
        'meets_target': p95 is not None and p95 <= target,
        'by_channel': dict(logs.values_list('channel').annotate(n=Count('pk')).order_by()),
        'daily': list(logs.annotate(day=TruncDate('created_at')).values('day')
                      .annotate(count=Count('pk')).order_by('day')),
        'recent': list(logs[:recent]),
    }
