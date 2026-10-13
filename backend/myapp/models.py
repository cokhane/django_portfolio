"""Content models for the portfolio: projects and core skills."""

from django.db import models


class Project(models.Model):
    """A portfolio piece rendered as a card in the projects grid."""

    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=40)
    description = models.TextField()
    tech_stack = models.JSONField(
        default=list,
        help_text="Display-only tag names, e.g. ['Django', 'React'].",
    )
    summary = models.TextField(blank=True, default="")
    problem = models.TextField(blank=True, default="")
    approach = models.TextField(blank=True, default="")
    result = models.TextField(blank=True, default="")
    role = models.CharField(max_length=40, blank=True, default="")
    year = models.CharField(max_length=12, blank=True, default="")
    repo_url = models.URLField(blank=True, default="")
    live_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "title")

    def __str__(self):
        return self.title


class Skill(models.Model):
    """One line in the CORE SKILLS panel."""

    name = models.CharField(max_length=120, unique=True)
    years = models.PositiveSmallIntegerField(
        default=0,
        help_text="Whole years of experience, set by the author. 0 is a real value.",
    )
    is_primary_focus = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name
