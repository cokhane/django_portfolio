"""Management command seeding the portfolio content."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from myapp.models import Project, Skill

PROJECTS = [
    (
        "E-Commerce Platform",
        "Web App",
        (
            "A full-featured online store with payment integration, inventory "
            "management, and admin dashboard built with Django and React."
        ),
        ["Django", "React", "PostgreSQL"],
    ),
    (
        "Tech Blog Platform",
        "Blog",
        (
            "Modern blogging platform with markdown support, comments, user "
            "authentication, and SEO optimization."
        ),
        ["Django", "Tailwind", "SQLite"],
    ),
    (
        "Analytics Dashboard",
        "Dashboard",
        (
            "Real-time analytics dashboard with beautiful charts, data "
            "visualization, and export functionality."
        ),
        ["Django", "Chart.js", "REST API"],
    ),
    (
        "Social Network",
        "Social",
        (
            "Social networking platform with posts, likes, comments, followers, "
            "and real-time notifications."
        ),
        ["Django", "WebSockets", "Redis"],
    ),
    (
        "Task Manager",
        "Productivity",
        (
            "Project management tool with kanban boards, task tracking, team "
            "collaboration, and deadlines."
        ),
        ["Django", "Vue.js", "MySQL"],
    ),
    (
        "Portfolio Builder",
        "Portfolio",
        (
            "Dynamic portfolio builder with drag-and-drop interface, custom "
            "themes, and export options."
        ),
        ["Django", "Alpine.js", "Tailwind"],
    ),
]

SKILLS = [
    "Django / Python / FastApi",
    "React / Next.js / Tailwind CSS",
    "AWS / Digital Ocean / Azure",
    "Linux / Jenkins / Docker",
]


class Command(BaseCommand):
    """Load the portfolio content that used to be hardcoded in the template."""

    help = "Seed the database with the portfolio's projects and skills."

    @transaction.atomic
    def handle(self, *args, **options):
        for order, (title, category, description, tech_stack) in enumerate(PROJECTS):
            Project.objects.update_or_create(
                slug=slugify(title),
                defaults={
                    "title": title,
                    "category": category,
                    "description": description,
                    "tech_stack": tech_stack,
                    "display_order": order,
                },
            )

        for order, name in enumerate(SKILLS):
            Skill.objects.update_or_create(
                name=name, defaults={"display_order": order}
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PROJECTS)} projects and {len(SKILLS)} skills."
            )
        )
