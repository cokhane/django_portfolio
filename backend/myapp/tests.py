"""Tests for the portfolio content models and read-only API."""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Project, Skill

REQUIRED_PROJECT = {
    "title": "Subscription Platform",
    "slug": "subscription-platform",
    "category": "PAYMENTS & COMMERCE",
    "description": "The card line today, until US-3.4-FE renders summary.",
}

CASE_STUDY = {
    "summary": "Built in two weeks. Opened a new revenue stream.",
    "problem": "A commerce business had no recurring-revenue product.",
    "approach": "A backend on Repository, Unit of Work and Factory patterns.",
    "result": "Delivered inside the deadline.\n\nIt now takes 1,000+ orders a day.",
    "role": "Solo build",
    "year": "2020\u20132023",
    "repo_url": "",
    "live_url": "https://example.com/live",
    "image_url": "https://example.com/cover.png",
    "is_published": True,
}


class ProjectModelTests(TestCase):
    """The case-study fields BRD S5 names, stored against a Project."""

    def test_is_published_defaults_to_false(self):
        """A project saved with only its required fields is a draft."""
        project = Project.objects.create(**REQUIRED_PROJECT)

        project.refresh_from_db()

        self.assertFalse(project.is_published)

    def test_case_study_fields_round_trip(self):
        """Every new field returns from the database exactly as stored."""
        Project.objects.create(**REQUIRED_PROJECT, **CASE_STUDY)

        project = Project.objects.get(slug=REQUIRED_PROJECT["slug"])

        for field, expected in CASE_STUDY.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(project, field), expected)

    def test_year_holds_a_range(self):
        """year is text, so it carries the MSP entry's four-year range."""
        Project.objects.create(**REQUIRED_PROJECT, year="2020\u20132023")

        project = Project.objects.get(slug=REQUIRED_PROJECT["slug"])

        self.assertEqual(project.year, "2020\u20132023")

    def test_ordering_is_unchanged(self):
        """display_order still orders the grid; the API contract rests on it."""
        Project.objects.create(**REQUIRED_PROJECT, display_order=1)
        Project.objects.create(
            title="Earlier",
            slug="earlier",
            category="CLOUD & DATA",
            description="Sorts first on display_order.",
            display_order=0,
        )

        titles = [project.title for project in Project.objects.all()]

        self.assertEqual(titles, ["Earlier", "Subscription Platform"])


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
        Skill.objects.create(
            name="Beta", display_order=1, years=11, is_primary_focus=True
        )
        Skill.objects.create(name="Alpha", display_order=0)

    def payload_by_name(self):
        """The list payload keyed by skill name, so tests ignore ordering."""
        response = self.client.get(reverse("skill-list"))

        return {skill["name"]: skill for skill in response.json()}

    def test_list_is_ordered_by_display_order(self):
        """Results follow display_order, not insertion order."""
        response = self.client.get(reverse("skill-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [skill["name"] for skill in response.json()], ["Alpha", "Beta"]
        )

    def test_list_exposes_the_fields_the_frontend_renders(self):
        """The payload carries exactly the fields the panel uses."""
        response = self.client.get(reverse("skill-list"))

        self.assertEqual(
            set(response.json()[0]),
            {"id", "name", "years", "is_primary_focus"},
        )

    def test_years_and_focus_round_trip(self):
        """Author-set values survive storage and serialization unchanged."""
        beta = self.payload_by_name()["Beta"]

        self.assertEqual(beta["years"], 11)
        self.assertTrue(beta["is_primary_focus"])

    def test_zero_years_serializes_as_zero(self):
        """A skill at zero years sends 0, not null and not an absent key."""
        alpha = self.payload_by_name()["Alpha"]

        self.assertIn("years", alpha)
        self.assertEqual(alpha["years"], 0)

    def test_api_is_read_only(self):
        """Writes are rejected; skills are edited through the admin."""
        response = self.client.post(reverse("skill-list"), {"name": "Nope"})

        self.assertEqual(response.status_code, 405)


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
