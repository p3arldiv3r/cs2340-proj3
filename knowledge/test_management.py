"""Tests for the Administrator clear/reload knowledge base story.
Run: python manage.py test knowledge.test_management"""
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from knowledge.ingestion import IngestionError, get_ingestor
from knowledge.models import Source, Document, Chunk
from knowledge.pipeline import ingest_source
from assistant.rag import answer_question

SAMPLE = settings.BASE_DIR / 'sample_data'


class ManageKnowledgeTests(TestCase):
    def setUp(self):
        for name in ['programs.json', 'faq.txt']:
            ingest_source(Source(method='upload', location=str(SAMPLE / name)))
        self.documents = Document.objects.count()
        self.client.force_login(get_user_model().objects.create_user(username='staff', is_staff=True))
        self.url = reverse('knowledge:manage')

    def post(self, **data):
        return self.client.post(self.url, data, follow=True)

    def test_page_shows_counts_and_sources(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'programs.json')
        self.assertContains(response, 'faq.txt')
        self.assertEqual(response.context['document_count'], self.documents)
        self.assertEqual(response.context['chunk_count'], Chunk.objects.count())

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'action': 'clear', 'confirm': 'yes'}).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user(username='visitor'))
        self.assertEqual(self.client.post(self.url, {'action': 'clear', 'confirm': 'yes'}).status_code, 302)
        self.assertEqual(Document.objects.count(), self.documents)

    def test_clear_requires_confirmation(self):
        response = self.post(action='clear')
        self.assertContains(response, 'Tick the confirmation box')
        self.assertEqual(Document.objects.count(), self.documents)

    def test_clear_removes_documents_and_keeps_sources(self):
        response = self.post(action='clear', confirm='yes')
        self.assertContains(response, f'Cleared {self.documents} documents')
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(Chunk.objects.count(), 0)
        self.assertEqual(Source.objects.count(), 2)
        self.assertEqual(answer_question('Chair Yoga').sources, ())

    def test_clear_can_also_forget_sources(self):
        self.post(action='clear', confirm='yes', forget_sources='yes')
        self.assertEqual(Source.objects.count(), 0)
        self.assertEqual(Document.objects.count(), 0)

    def test_reload_restores_after_clear(self):
        self.post(action='clear', confirm='yes')
        response = self.post(action='reload')
        self.assertContains(response, f'Reloaded {self.documents} documents from 2 sources')
        self.assertEqual(Document.objects.count(), self.documents)
        self.assertEqual(answer_question('Chair Yoga').sources[0].external_id, 'prog-101')

    def test_reload_replaces_outdated_and_manual_edits(self):
        document = Document.objects.get(external_id='prog-101')
        document.text = 'Outdated text'
        document.save()
        Document.objects.create(source=document.source, external_id='stale', title='Stale',
                                text='Stale', content_hash='x')
        self.post(action='reload')
        self.assertFalse(Document.objects.filter(external_id='stale').exists())
        self.assertIn('Gentle stretches', Document.objects.get(external_id='prog-101').text)
        self.assertEqual(Document.objects.count(), self.documents)

    def test_failed_reload_keeps_all_existing_documents(self):
        before = list(Document.objects.values_list('pk', flat=True))
        # The second source fails after the first is re-ingested: the whole reload rolls back.
        calls = []
        def flaky(method):
            calls.append(method)
            if len(calls) == 2:
                raise IngestionError('Source unavailable')
            return get_ingestor(method)
        with patch('knowledge.pipeline.get_ingestor', side_effect=flaky):
            with self.assertLogs('knowledge.views', level='ERROR'):
                response = self.post(action='reload')
        self.assertContains(response, 'Reload failed')
        self.assertContains(response, 'Source unavailable')
        self.assertEqual(list(Document.objects.values_list('pk', flat=True)), before)

    def test_reload_with_no_sources(self):
        Source.objects.all().delete()
        self.assertContains(self.post(action='reload'), 'no sources to reload')

    def test_unknown_action_and_get_change_nothing(self):
        self.assertContains(self.post(action='drop-tables'), 'Unknown action')
        self.client.get(self.url, {'action': 'clear', 'confirm': 'yes'})
        self.assertEqual(Document.objects.count(), self.documents)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(get_user_model().objects.get(username='staff'))
        self.assertEqual(client.post(self.url, {'action': 'clear', 'confirm': 'yes'}).status_code, 403)
        self.assertEqual(Document.objects.count(), self.documents)
