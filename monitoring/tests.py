"""Tests for the Administrator monitoring and usage-log stories.
Run: python manage.py test monitoring"""
from datetime import timedelta
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from knowledge.models import Source
from knowledge.pipeline import ingest_source
from .models import QueryLog
from .services import percentile, summarize


def log(latency_ms=100, succeeded=True, source_count=1, channel=QueryLog.PAGE, age=None, **fields):
    entry = QueryLog.objects.create(latency_ms=latency_ms, succeeded=succeeded,
                                    source_count=source_count, channel=channel, **fields)
    if age is not None:
        QueryLog.objects.filter(pk=entry.pk).update(created_at=timezone.now() - age)
    return entry


class RecordingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ingest_source(Source(method='upload', location=str(settings.BASE_DIR / 'sample_data/programs.json')))

    def test_page_question_is_logged_with_latency_and_sources(self):
        self.client.post(reverse('assistant:chat'), {'question': 'Chair Yoga'})
        entry = QueryLog.objects.get()
        self.assertEqual(entry.channel, QueryLog.PAGE)
        self.assertTrue(entry.succeeded)
        self.assertGreaterEqual(entry.source_count, 1)
        self.assertGreaterEqual(entry.latency_ms, 0)
        self.assertIsNotNone(entry.created_at)

    def test_popup_question_is_logged(self):
        self.client.post(reverse('assistant:ask'), {'question': 'Chair Yoga'})
        self.assertEqual(QueryLog.objects.get().channel, QueryLog.POPUP)

    def test_unanswered_question_logged_as_success_without_sources(self):
        self.client.post(reverse('assistant:ask'), {'question': 'quantum astrophysics'})
        entry = QueryLog.objects.get()
        self.assertTrue(entry.succeeded)
        self.assertEqual(entry.source_count, 0)
        self.assertFalse(entry.answered)

    def test_failure_is_logged_with_error_type_only(self):
        with patch('assistant.views.answer_question', side_effect=RuntimeError('private details')):
            with self.assertLogs('assistant.views', level='ERROR'):
                self.client.post(reverse('assistant:ask'), {'question': 'Yoga'})
        entry = QueryLog.objects.get()
        self.assertFalse(entry.succeeded)
        self.assertEqual(entry.error_type, 'RuntimeError')

    def test_invalid_question_is_not_logged(self):
        self.client.post(reverse('assistant:ask'), {'question': '   '})
        self.assertFalse(QueryLog.objects.exists())

    def test_question_text_is_not_stored(self):
        self.client.post(reverse('assistant:chat'), {'question': 'My secret Chair Yoga question'})
        entry = QueryLog.objects.values().get()
        self.assertNotIn('My secret', ' '.join(str(v) for v in entry.values()))

    def test_logging_failure_does_not_break_chat(self):
        with patch('monitoring.services.QueryLog.objects.create', side_effect=RuntimeError('db down')):
            with self.assertLogs('monitoring.services', level='ERROR'):
                response = self.client.post(reverse('assistant:ask'), {'question': 'Chair Yoga'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['sources'][0]['external_id'], 'prog-101')


class SummaryTests(TestCase):
    def test_empty_summary(self):
        summary = summarize()
        self.assertEqual(summary['total'], 0)
        self.assertEqual(summary['failure_rate'], 0)
        self.assertIsNone(summary['avg_ms'])
        self.assertIsNone(summary['p95_ms'])
        self.assertFalse(summary['meets_target'])

    def test_percentile_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(percentile(values, 0.5), 50)
        self.assertEqual(percentile(values, 0.95), 95)
        self.assertEqual(percentile([7], 0.95), 7)
        self.assertIsNone(percentile([], 0.5))

    @override_settings(ASSISTANT_LATENCY_TARGET_MS=500)
    def test_latency_and_failure_metrics(self):
        for latency in [100, 200, 300, 400]:
            log(latency)
        log(900, succeeded=False, source_count=0, error_type='RuntimeError')
        log(150, source_count=0, channel=QueryLog.POPUP)
        summary = summarize()
        self.assertEqual(summary['total'], 6)
        self.assertEqual(summary['failures'], 1)
        self.assertAlmostEqual(summary['failure_rate'], 1 / 6)
        self.assertEqual(summary['unanswered'], 1)
        self.assertEqual(summary['avg_ms'], round(2050 / 6))
        self.assertEqual(summary['max_ms'], 900)
        self.assertEqual(summary['p95_ms'], 900)
        self.assertEqual(summary['slow'], 1)
        self.assertFalse(summary['meets_target'])
        self.assertEqual(summary['by_channel'], {'page': 5, 'popup': 1})

    @override_settings(ASSISTANT_LATENCY_TARGET_MS=500)
    def test_meets_target_when_p95_under_target(self):
        for _ in range(20):
            log(100)
        self.assertTrue(summarize()['meets_target'])

    def test_period_excludes_older_logs(self):
        log(age=timedelta(days=2))
        log(age=timedelta(days=10))
        log()
        self.assertEqual(summarize(days=1)['total'], 1)
        self.assertEqual(summarize(days=7)['total'], 2)
        self.assertEqual(summarize(days=30)['total'], 3)

    def test_daily_counts_and_recent_order(self):
        old = log(age=timedelta(days=1))
        newer = log()
        newest = log()
        summary = summarize()
        self.assertEqual([row['count'] for row in summary['daily']], [1, 2])
        self.assertEqual(summary['recent'], [newest, newer, old])

    def test_recent_is_limited(self):
        for _ in range(5):
            log()
        self.assertEqual(len(summarize(recent=3)['recent']), 3)


class DashboardTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='staff', is_staff=True))

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('monitoring:dashboard')).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user(username='visitor'))
        self.assertEqual(self.client.get(reverse('monitoring:dashboard')).status_code, 302)

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse('monitoring:dashboard')), 'No questions yet')

    @override_settings(ASSISTANT_LATENCY_TARGET_MS=500)
    def test_shows_metrics_and_recent_log(self):
        log(120)
        log(80, succeeded=False, source_count=0, error_type='RuntimeError', channel=QueryLog.POPUP)
        response = self.client.get(reverse('monitoring:dashboard'))
        self.assertContains(response, 'data-status="ok"')
        self.assertContains(response, '120 ms')
        self.assertContains(response, 'Failed (RuntimeError)')
        self.assertContains(response, 'Answered, 1 source')
        self.assertContains(response, '50%')
        self.assertEqual(response.context['summary']['total'], 2)

    @override_settings(ASSISTANT_LATENCY_TARGET_MS=500)
    def test_flags_slow_responses(self):
        log(5000)
        self.assertContains(self.client.get(reverse('monitoring:dashboard')), 'data-status="slow"')

    def test_period_selection(self):
        log(age=timedelta(days=3))
        self.assertEqual(self.client.get(reverse('monitoring:dashboard'), {'days': 1}).context['summary']['total'], 0)
        self.assertEqual(self.client.get(reverse('monitoring:dashboard'), {'days': 7}).context['summary']['total'], 1)
        for bad in ['abc', '9999', '-1']:
            self.assertEqual(self.client.get(reverse('monitoring:dashboard'), {'days': bad}).context['summary']['days'], 7)

    def test_admin_log_is_read_only(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='x')
        self.client.force_login(admin)
        entry = log()
        self.assertEqual(self.client.get(reverse('admin:monitoring_querylog_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:monitoring_querylog_add')).status_code, 403)
        self.assertContains(self.client.get(reverse('admin:monitoring_querylog_change', args=[entry.pk])), 'readonly')
