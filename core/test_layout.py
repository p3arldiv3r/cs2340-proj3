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
                self.assertContains(response, 'data-color="high-contrast"')
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

    def test_staff_menu_only_for_staff(self):
        self.assertNotContains(self.client.get(reverse('core:home')), 'data-staff-menu')
        self.client.force_login(get_user_model().objects.create_user(username='visitor'))
        self.assertNotContains(self.client.get(reverse('core:home')), 'data-staff-menu')
        self.client.force_login(get_user_model().objects.create_user(username='staff', is_staff=True))
        response = self.client.get(reverse('monitoring:dashboard'))
        self.assertContains(response, 'data-staff-menu', count=1)
        for name in ['knowledge:manage', 'evaluation:runs', 'admin:index']:
            self.assertContains(response, reverse(name))
        self.assertContains(response, f'href="{reverse("monitoring:dashboard")}" aria-current="page"')

    def test_prefilled_activity_question_is_escaped(self):
        response = self.client.get(reverse('assistant:chat'), {'question': '<script>alert(1)</script>'})
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_admin_uses_garden_theme(self):
        user = get_user_model().objects.create_superuser(username='admin', password='x')
        self.client.force_login(user)
        for url in [reverse('admin:index'), reverse('admin:monitoring_querylog_changelist')]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'core/garden.css')
                self.assertContains(response, 'core/garden-admin.css')
                self.assertContains(response, 'data-color="high-contrast"')
                self.assertContains(response, reverse('monitoring:dashboard'))
                self.assertNotContains(response, 'admin/css/dark_mode.css')
                self.assertNotContains(response, 'theme-toggle')

    def test_admin_login_uses_garden_theme(self):
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, 'core/garden-admin.css')
        self.assertNotContains(response, 'Staff navigation')
