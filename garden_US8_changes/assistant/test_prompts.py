"""US8 acceptance tests: intent detection and different grounded answers."""
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from knowledge.models import Source
from knowledge.pipeline import ingest_source
from .prompts import classify_intent, select_prompt
from .rag import answer_question


class IntentTests(SimpleTestCase):
    def test_question_types_are_distinguished(self):
        examples = {
            'Who teaches Chair Yoga?': 'factual',
            'When does the Afternoon Book Circle meet?': 'factual',
            'How much does Watercolor Basics cost?': 'factual',
            'How do the community groups work?': 'explanation',
            'What happens at Chair Yoga?': 'explanation',
            'Can you suggest a free online activity?': 'recommendation',
            'Find free online morning activities': 'recommendation',
            'I am looking for book groups': 'recommendation',
        }
        for question, expected in examples.items():
            with self.subTest(question=question):
                self.assertEqual(classify_intent(question), expected)

    def test_prompt_plans_change_the_actual_answer_strategy(self):
        factual = select_prompt('When does the book circle meet?')
        explaining = select_prompt('How does the book circle work?')
        recommending = select_prompt('Suggest a book circle')
        self.assertEqual(factual.max_sources, 1)
        self.assertEqual(factual.sentences_per_source, 1)
        self.assertGreater(explaining.sentences_per_source, factual.sentences_per_source)
        self.assertEqual(recommending.max_sources, 2)
        self.assertIn('cite', recommending.instruction)


class AnswerStyleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ingest_source(Source(method='upload', location=str(settings.BASE_DIR / 'sample_data/programs.json')))
        ingest_source(Source(method='upload', location=str(settings.BASE_DIR / 'sample_data/book_circle.md')))

    def test_explanation_has_context_but_no_recommendation_cards(self):
        answer = answer_question('What happens at Chair Yoga?')
        self.assertEqual(answer.intent, 'explanation')
        self.assertEqual(answer.recommendations, ())
        self.assertIn('Gentle stretches', answer.text)
        self.assertIn('Online', answer.text)
        self.assertEqual([s.external_id for s in answer.sources], ['prog-101'])

    def test_factual_lookup_is_short_and_grounded(self):
        answer = answer_question('Who teaches Chair Yoga?')
        self.assertEqual(answer.intent, 'factual')
        self.assertIn('Jordan Lee', answer.text)
        self.assertEqual([s.external_id for s in answer.sources], ['prog-101'])
        self.assertFalse(answer.recommendations)

    def test_factual_metadata_answer_is_direct_and_verifiable(self):
        answer = answer_question('Is Chair Yoga free?')
        self.assertEqual(answer.intent, 'factual')
        self.assertEqual(answer.text, 'Chair Yoga is free. [1]')
        self.assertEqual(answer.sources[0].excerpt, 'Cost: Free')

    def test_recommendations_use_real_activity_metadata_and_two_max(self):
        answer = answer_question('Find free online morning activities')
        self.assertEqual(answer.intent, 'recommendation')
        self.assertEqual([r.title for r in answer.recommendations], ['Chair Yoga'])
        self.assertEqual(answer.recommendations[0].tags, ('Online', 'Morning', 'Free'))
        self.assertEqual(answer.recommendations[0].source_number, answer.sources[0].number)
        self.assertNotIn('Coffee and Conversation', [r.title for r in answer.recommendations])

    def test_no_match_does_not_invent_a_recommendation(self):
        answer = answer_question('suggest a quantum astrophysics class')
        self.assertEqual(answer.sources, ())
        self.assertEqual(answer.recommendations, ())
        self.assertIn("couldn't find", answer.text)

    def test_full_page_displays_compact_cards_and_sources(self):
        response = self.client.post(reverse('assistant:chat'), {
            'question': 'Find free online morning activities',
        })
        self.assertContains(response, 'recommendation-card')
        self.assertContains(response, 'Suggestions')
        self.assertContains(response, 'Chair Yoga')
        self.assertContains(response, 'Source 1: Chair Yoga')
        self.assertNotContains(response, 'Coffee and Conversation')

    def test_popup_returns_structured_answer_using_same_rules(self):
        response = self.client.post(reverse('assistant:ask'), {
            'question': 'Find free online morning activities',
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['intent'], 'recommendation')
        self.assertEqual(result['recommendations'][0]['title'], 'Chair Yoga')
        self.assertEqual(result['recommendations'][0]['source_number'], 1)
        self.assertEqual(result['sources'][0]['external_id'], 'prog-101')
