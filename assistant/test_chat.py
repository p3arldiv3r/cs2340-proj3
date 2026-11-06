from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from knowledge.models import Source, Document, Chunk
from knowledge.pipeline import ingest_source
from knowledge.ingestion import IngestionError
from knowledge.retrieval import retrieve
from .rag import answer_question


class ChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.source = Source(method='upload', location=str(settings.BASE_DIR / 'sample_data/programs.json'))
        ingest_source(cls.source)

    def test_question_returns_supporting_record_and_metadata(self):
        answer = answer_question('What happens at Chair Yoga?')
        self.assertIn('Gentle stretches', answer.text)
        self.assertIn('Online', answer.text)
        self.assertEqual(answer.sources[0].external_id, 'prog-101')
        self.assertIn(answer.sources[0].excerpt, Document.objects.get(external_id='prog-101').text)

    def test_explicit_filters_exclude_incompatible_programs(self):
        results = retrieve('Find free online morning activities')
        self.assertEqual([p.chunk.document.external_id for p in results], ['prog-101'])

    def test_unrelated_or_empty_query_has_no_sources(self):
        for question in ['quantum astrophysics', '', 'the and of']:
            answer = answer_question(question)
            self.assertEqual(answer.sources, ())
            self.assertIn("couldn't find", answer.text)

    def test_reingestion_replaces_without_duplicates(self):
        ingest_source(self.source)
        self.assertEqual(Document.objects.count(), 3)
        self.assertEqual(Chunk.objects.count(), 3)

    def test_failed_fetch_preserves_existing_documents(self):
        with patch('knowledge.pipeline.get_ingestor') as factory:
            factory.return_value.fetch.side_effect = IngestionError('Unavailable')
            with self.assertRaises(IngestionError):
                ingest_source(self.source)
        self.assertEqual(Document.objects.count(), 3)

    def test_chunks_from_same_document_have_one_citation(self):
        document = Document.objects.get(external_id='prog-101')
        Chunk.objects.create(document=document, position=1, text='Chair Yoga offers seated stretches for a gentle morning.')
        answer = answer_question('Chair Yoga')
        self.assertEqual(len(answer.sources), 1)

    def test_public_chat_get_and_post(self):
        url = reverse('assistant:chat')
        self.assertContains(self.client.get(url), 'Your question')
        response = self.client.post(url, {'question': 'Chair Yoga'})
        self.assertContains(response, 'Source 1: Chair Yoga')
        self.assertContains(response, 'prog-101')
        self.assertContains(response, 'Gentle stretches')

    def test_empty_and_overlong_questions_rejected(self):
        for question in ['   ', 'x' * 1001]:
            response = self.client.post(reverse('assistant:chat'), {'question': question})
            self.assertTrue(response.context['form'].errors)
            self.assertIsNone(response.context['answer'])

    def test_csrf_required(self):
        response = Client(enforce_csrf_checks=True).post(reverse('assistant:chat'), {'question': 'Yoga'})
        self.assertEqual(response.status_code, 403)

    def test_question_and_source_text_are_escaped(self):
        document = Document.objects.get(external_id='prog-101')
        document.title = '<script>alert(1)</script> Chair Yoga'
        document.save()
        response = self.client.post(reverse('assistant:chat'), {'question': '<script>alert(2)</script> Chair Yoga'})
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_unsafe_source_url_not_exposed(self):
        document = Document.objects.first()
        for url in ['javascript:alert(1)', 'https://[invalid']:
            document.metadata = {'url': url}
            self.assertEqual(document.public_url, '')

    def test_service_error_is_friendly(self):
        with patch('assistant.views.answer_question', side_effect=RuntimeError('private details')):
            with self.assertLogs('assistant.views', level='ERROR'):
                response = self.client.post(reverse('assistant:chat'), {'question': 'Yoga'})
        self.assertContains(response, 'Please try again shortly')
        self.assertNotContains(response, 'private details')

    def test_staff_pages_are_not_public(self):
        for path in ['/knowledge/', '/evaluation/', '/monitoring/']:
            self.assertEqual(self.client.get(path).status_code, 302)

    def test_original_url_is_shown(self):
        document = Document.objects.get(external_id='prog-101')
        document.metadata['url'] = 'https://example.org/yoga'
        document.save()
        self.assertContains(self.client.post(reverse('assistant:chat'), {'question': 'Chair Yoga'}), 'https://example.org/yoga')

    def test_popup_endpoint_returns_same_answer_and_citations(self):
        response = self.client.post(reverse('assistant:ask'), {'question': 'Chair Yoga'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['text'], answer_question('Chair Yoga').text)
        self.assertEqual(response.json()['sources'][0]['external_id'], 'prog-101')

    def test_popup_endpoint_validates_input_and_method(self):
        self.assertEqual(self.client.get(reverse('assistant:ask')).status_code, 405)
        for question in ['', '   ', 'x' * 1001]:
            response = self.client.post(reverse('assistant:ask'), {'question': question})
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())

    def test_popup_endpoint_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse('assistant:ask'), {'question': 'Yoga'})
        self.assertEqual(response.status_code, 403)

    def test_popup_service_error_is_friendly(self):
        with patch('assistant.views.answer_question', side_effect=RuntimeError('private details')):
            with self.assertLogs('assistant.views', level='ERROR'):
                response = self.client.post(reverse('assistant:ask'), {'question': 'Yoga'})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private details', response.content.decode())
