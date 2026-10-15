"""Admin registrations for editing portfolio content."""

from typing import ClassVar

from django.contrib import admin

from .models import Availability, Engagement, Project, Skill


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin for editing portfolio projects."""

    list_display = ("title", "category", "is_published", "display_order")
    list_editable = ("display_order",)
    list_filter = ("is_published",)
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        "slug": ("title",)
    }
    # The case study opens on `result`: the outcome is written first and the
    # problem, approach and card copy are drawn from it, so the form follows
    # the order the author writes in rather than the model's declaration order.
    # `is_published` sits last — publishing is the deliberate closing action.
    fieldsets: ClassVar[tuple[tuple[str, dict[str, tuple[str, ...]]], ...]] = (
        ("Identity", {
            "fields": ("title", "slug", "category", "role", "year", "tech_stack"),
        }),
        ("Case study", {
            "fields": ("result", "problem", "approach", "summary", "description"),
        }),
        ("Links", {
            "fields": ("repo_url", "live_url", "image_url"),
        }),
        ("Publication", {
            "fields": ("display_order", "is_published"),
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin for editing core skills."""

    list_display = ("name", "years", "is_primary_focus", "display_order")
    list_editable = ("years", "display_order")


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    """Admin for the "what I take on" cards."""

    list_display = ("label", "display_order")
    list_editable = ("display_order",)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    """Admin for the one availability row: editable, never duplicable."""

    list_display = ("state", "available_from")

    def has_add_permission(self, request):
        """Offer Add only while there is no row to edit.

        This reads the state of the table; it does not restate the singleton
        rule, which the database holds. Without it the Add button would still
        be there and would fail with an `IntegrityError` — honest, but a poor
        thing to show an author. Delete stays available: removing the row is
        the author's way of saying nothing, and the endpoint answers with the
        documented empty shape again.
        """
        return super().has_add_permission(request) and not Availability.objects.exists()
