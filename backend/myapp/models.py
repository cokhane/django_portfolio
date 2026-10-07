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
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "title")

    def __str__(self):
        return self.title


class Skill(models.Model):
    """One line in the CORE SKILLS panel."""

    name = models.CharField(max_length=120, unique=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name
