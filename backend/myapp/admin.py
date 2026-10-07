"""Admin registrations for editing portfolio content."""

from typing import ClassVar

from django.contrib import admin

from .models import Project, Skill


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin for editing portfolio projects."""

    list_display = ("title", "category", "display_order")
    list_editable = ("display_order",)
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        "slug": ("title",)
    }


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin for editing core skills."""

    list_display = ("name", "display_order")
    list_editable = ("display_order",)
