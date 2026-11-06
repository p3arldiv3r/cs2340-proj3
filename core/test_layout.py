from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LayoutTests(TestCase):
    def test_public_pages_share_popup_and_reading_controls(self):
        for name in ['core:home', 'core:activities', 'core:help', 'assistant:chat']:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'id="chat-popup"', count=1)
                self.assertContains(response, 'data-open-chat', count=1)
                self.assertContains(response, 'data-text-size="largest"')
                self.assertContains(response, 'data-contrast')
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertContains(response, 'core/garden.js')
                self.assertNotContains(response, 'Placeholder page')

    def test_page_and_popup_have_distinct_input_ids(self):
        response = self.client.get(reverse('assistant:chat'))
        self.assertContains(response, 'id="page-question"', count=1)
        self.assertContains(response, 'id="popup-question"', count=1)

    def test_staff_pages_also_have_popup(self):
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        self.client.force_login(user)
        for name in ['knowledge:manage', 'evaluation:runs', 'monitoring:dashboard']:
            self.assertContains(self.client.get(reverse(name)), 'id="chat-popup"', count=1)

    def test_prefilled_activity_question_is_escaped(self):
        response = self.client.get(reverse('assistant:chat'), {'question': '<script>alert(1)</script>'})
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
