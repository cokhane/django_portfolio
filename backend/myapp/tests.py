"""Tests for the portfolio content models and read-only API."""

import re
from itertools import chain

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .admin import ProjectAdmin
from .models import Project, Skill
from .serializers import ProjectDetailSerializer

REQUIRED_PROJECT = {
    "title": "Subscription Platform",
    "slug": "subscription-platform",
    "category": "PAYMENTS & COMMERCE",
    "description": "The card line today, until US-3.4-FE renders summary.",
}

PUBLISHED_CARDS = (
    {
        "title": "Second",
        "slug": "second",
        "category": "Blog",
        "description": "Second project.",
        "tech_stack": ["Django"],
        "display_order": 1,
    },
    {
        "title": "First",
        "slug": "first",
        "category": "Web App",
        "description": "First project.",
        "tech_stack": ["Django", "React"],
        "display_order": 0,
    },
)

# display_order 0 would sort this first if the queryset were not filtered,
# so its absence proves the filter rather than merely the ordering.
DRAFT_CARD = {
    "title": "Draft",
    "slug": "draft",
    "category": "Web App",
    "description": "Unpublished, so no endpoint may return it.",
    "display_order": 0,
}

LIST_PAYLOAD_KEYS = {"slug", "title", "category", "summary", "description", "tech_stack"}

# Written out in full rather than derived from LIST_PAYLOAD_KEYS: deriving it
# would let an edit to the list set move this expectation silently, which is
# the exact payload drift the exact-key-set assertions exist to catch.
DETAIL_PAYLOAD_KEYS = {
    "slug", "title", "category", "summary", "description", "tech_stack",
    "problem", "approach", "result", "role", "year",
    "repo_url", "live_url", "image_url",
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
        for card in PUBLISHED_CARDS:
            Project.objects.create(**card, is_published=True)
        Project.objects.create(**DRAFT_CARD)

    def test_list_returns_only_published_projects(self):
        """Published rows are present; a draft is absent. BRD F-6."""
        response = self.client.get(reverse("project-list"))

        titles = {project["title"] for project in response.json()}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(titles, {"First", "Second"})
        self.assertNotIn("Draft", titles)

    def test_list_is_ordered_by_display_order(self):
        """Ordering still holds over the published-only queryset."""
        response = self.client.get(reverse("project-list"))

        titles = [project["title"] for project in response.json()]
        self.assertEqual(titles, ["First", "Second"])

    def test_list_exposes_the_fields_the_frontend_renders(self):
        """The payload carries exactly the fields a card needs."""
        response = self.client.get(reverse("project-list"))

        self.assertEqual(set(response.json()[0]), LIST_PAYLOAD_KEYS)

    def test_list_payload_carries_no_case_study(self):
        """The card payload stays small — the prose belongs to the detail."""
        card = self.client.get(reverse("project-list")).json()[0]

        for field in ("problem", "approach", "result"):
            with self.subTest(field=field):
                self.assertNotIn(field, card)

    def test_tech_stack_round_trips_as_a_list(self):
        """tech_stack survives JSONField storage as a real list."""
        response = self.client.get(reverse("project-list"))

        self.assertEqual(response.json()[0]["tech_stack"], ["Django", "React"])

    def test_api_is_read_only(self):
        """Writes are rejected; content is edited through the admin."""
        response = self.client.post(reverse("project-list"), {"title": "Nope"})

        self.assertEqual(response.status_code, 405)


class ProjectDetailSerializerTests(TestCase):
    """The detail payload's shape, before US-3.1-BE routes anything to it."""

    def test_detail_payload_key_set(self):
        """The case study rides alongside the card fields, minus the internals."""
        project = Project.objects.create(**REQUIRED_PROJECT, **CASE_STUDY)

        payload = ProjectDetailSerializer(project).data

        self.assertEqual(set(payload), DETAIL_PAYLOAD_KEYS)


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


BRD_CATEGORIES = {
    "AI PLATFORMS", "MULTI-TENANT SAAS", "PAYMENTS & COMMERCE", "CLOUD & DATA",
}

PROSE_FIELDS = ("title", "summary", "problem", "approach", "result")

# NFR-6: no published text names a client, employer or platform. Two kinds of term:
# `uma` is the one platform name the BRD's shortlist table still carries and the
# case studies anonymised away, so it is the transcription error most likely to
# recur; the rest mark a company's legal name, which is how an employer usually
# arrives. Matched whole-word against tokenised text, so `inc` cannot fire on
# "increased". Extend it when a name is identified — the terms belong here, not
# in the seeded content.
DENIED_NAME_TOKENS = frozenset({
    "uma", "inc", "ltd", "llc", "gmbh", "pty", "corp", "plc", "holdings",
    "sarl", "bv", "ag", "srl",
})

# Written out rather than imported from the command: importing would let a slug
# dropped from SUPERSEDED_SLUGS pass this test silently, which is the regression
# it exists to catch. Same reasoning as DETAIL_PAYLOAD_KEYS above.
PLACEHOLDER_SLUGS = (
    "e-commerce-platform", "tech-blog-platform", "analytics-dashboard",
    "social-network", "task-manager", "portfolio-builder",
)
PLACEHOLDER_SKILLS = (
    "Django / Python / FastApi", "React / Next.js / Tailwind CSS",
    "AWS / Digital Ocean / Azure", "Linux / Jenkins / Docker",
)


def labelled_text(project):
    """Every human-readable value on one row, labelled `(slug, field, value)`.

    Returning the label with the value lets the callers scan a flat sequence —
    one loop, no project-then-field nesting — and still name the offender.
    """
    values = {
        **{field: getattr(project, field) for field in PROSE_FIELDS},
        "category": project.category,
        "role": project.role,
        "tech_stack": " ".join(project.tech_stack),
    }
    return [(project.slug, field, value) for field, value in values.items()]


def labelled_text_of(projects):
    """`labelled_text` over many rows, flattened to one sequence."""
    return chain.from_iterable(map(labelled_text, projects))


def words_in(text):
    """The lowercase word tokens of `text`, so a match is never a substring."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class SeedCommandTests(TestCase):
    """`seed_portfolio` carries the real shortlist, anonymised and finished."""

    def setUp(self):
        call_command("seed_portfolio", verbosity=0)

    def test_seeding_is_idempotent(self):
        """Re-seeding updates in place rather than duplicating rows."""
        first_count = Project.objects.count()
        call_command("seed_portfolio", verbosity=0)

        self.assertEqual(Project.objects.count(), first_count)
        self.assertEqual(first_count, 8)
        self.assertEqual(Skill.objects.count(), 4)

    def test_no_published_text_holds_a_bracketed_prompt(self):
        """A published field still carrying `[` is an unanswered prompt on the site."""
        published = Project.objects.filter(is_published=True)

        for slug, field, value in labelled_text_of(published):
            with self.subTest(slug=slug, field=field):
                self.assertNotIn("[", value)

    def test_no_seeded_text_names_a_client_employer_or_platform(self):
        """NFR-6, over drafts too: a draft is published by one admin click."""
        rows = list(labelled_text_of(Project.objects.all()))
        rows += [
            ("skill", name, name)
            for name in Skill.objects.values_list("name", flat=True)
        ]

        for slug, field, value in rows:
            with self.subTest(slug=slug, field=field):
                self.assertEqual(words_in(value) & DENIED_NAME_TOKENS, set())

    def test_every_category_is_one_of_the_four(self):
        """A typo would add a fifth filter button to the grid."""
        seeded = set(Project.objects.values_list("category", flat=True))

        self.assertEqual(seeded - BRD_CATEGORIES, set())

    def test_superseded_placeholders_do_not_survive(self):
        """The invented content is removed, not merely left unpublished.

        Every placeholder is created, not just the first: seeding one would let
        any other slug be dropped from the command's list and still pass here.
        """
        Project.objects.bulk_create(
            Project(**{**REQUIRED_PROJECT, "title": slug, "slug": slug, "is_published": True})
            for slug in PLACEHOLDER_SLUGS
        )
        Skill.objects.bulk_create(Skill(name=name) for name in PLACEHOLDER_SKILLS)
        call_command("seed_portfolio", verbosity=0)

        self.assertFalse(Project.objects.filter(slug__in=PLACEHOLDER_SLUGS).exists())
        self.assertFalse(Skill.objects.filter(name__in=PLACEHOLDER_SKILLS).exists())

    def test_published_projects_are_complete(self):
        """The one entry that reaches the site carries every field that sells it."""
        for project in Project.objects.filter(is_published=True):
            with self.subTest(slug=project.slug):
                self.assertTrue(project.summary)
                self.assertTrue(project.approach)
                self.assertTrue(project.result)
                self.assertEqual(project.description, project.summary)


def editable_project_fields():
    """Every Project field the author types into, less the auto primary key.

    The implicit `id` is `auto_created`, not `editable=False` — Django hides it
    from forms by returning no formfield — so both conditions are needed here.
    """
    return {
        field.name
        for field in Project._meta.fields
        if field.editable and not field.auto_created
    }


def fields_placed_on_the_form():
    """Every field named by a ProjectAdmin fieldset, duplicates preserved."""
    return [
        field
        for _, options in ProjectAdmin.fieldsets
        for field in options["fields"]
    ]


class ProjectAdminTests(SimpleTestCase):
    """The admin form is the only way content is written. BRD F-11."""

    def test_every_editable_field_is_on_the_form(self):
        """A field added to Project and left off a fieldset fails here."""
        self.assertEqual(set(fields_placed_on_the_form()), editable_project_fields())

    def test_no_field_is_repeated_across_fieldsets(self):
        """Each field sits in exactly one group, so nothing is entered twice."""
        placed = fields_placed_on_the_form()

        self.assertEqual(len(placed), len(set(placed)))

    def test_the_case_study_opens_on_result(self):
        """result is written first and the rest of the case study follows it."""
        case_study = dict(ProjectAdmin.fieldsets)["Case study"]

        self.assertEqual(case_study["fields"][0], "result")
