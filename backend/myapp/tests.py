"""Tests for the portfolio content models and read-only API."""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Project, Skill


class ProjectAPITests(TestCase):
    """The projects endpoint is the frontend's only source of project data."""

    @classmethod
    def setUpTestData(cls):
        Project.objects.create(
            title="Second",
            slug="second",
            category="Blog",
            description="Second project.",
            tech_stack=["Django"],
            display_order=1,
        )
        Project.objects.create(
            title="First",
            slug="first",
            category="Web App",
            description="First project.",
            tech_stack=["Django", "React"],
            display_order=0,
        )

    def test_list_returns_every_project(self):
        """Every seeded project appears in the list response."""
        response = self.client.get(reverse("project-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_list_is_ordered_by_display_order(self):
        """Results follow display_order, not insertion order."""
        response = self.client.get(reverse("project-list"))

        titles = [project["title"] for project in response.json()]
        self.assertEqual(titles, ["First", "Second"])

    def test_list_exposes_the_fields_the_frontend_renders(self):
        """The payload carries exactly the fields the template uses."""
        response = self.client.get(reverse("project-list"))

        self.assertEqual(
            set(response.json()[0]),
            {"id", "title", "category", "description", "tech_stack"},
        )

    def test_tech_stack_round_trips_as_a_list(self):
        """tech_stack survives JSONField storage as a real list."""
        response = self.client.get(reverse("project-list"))

        self.assertEqual(response.json()[0]["tech_stack"], ["Django", "React"])

    def test_api_is_read_only(self):
        """Writes are rejected; content is edited through the admin."""
        response = self.client.post(reverse("project-list"), {"title": "Nope"})

        self.assertEqual(response.status_code, 405)


class SkillAPITests(TestCase):
    """The skills endpoint backs the CORE SKILLS panel."""

    @classmethod
    def setUpTestData(cls):
        Skill.objects.create(name="Beta", display_order=1)
        Skill.objects.create(name="Alpha", display_order=0)

    def test_list_is_ordered_by_display_order(self):
        """Results follow display_order, not insertion order."""
        response = self.client.get(reverse("skill-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [skill["name"] for skill in response.json()], ["Alpha", "Beta"]
        )


class SeedCommandTests(TestCase):
    """`seed_portfolio` carries the content that used to be hardcoded."""

    def test_seeding_is_idempotent(self):
        """Re-seeding updates in place rather than duplicating rows."""
        call_command("seed_portfolio", verbosity=0)
        first_count = Project.objects.count()
        call_command("seed_portfolio", verbosity=0)

        self.assertEqual(Project.objects.count(), first_count)
        self.assertEqual(first_count, 6)
        self.assertEqual(Skill.objects.count(), 4)
