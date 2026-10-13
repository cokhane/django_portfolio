"""Serializers translating portfolio models into the API payload."""

from rest_framework import serializers

from .models import Project, Skill


class ProjectListSerializer(serializers.ModelSerializer):
    """Serialize a Project into the small payload a grid card renders.

    Deliberately omits the case-study prose: a grid of cards would otherwise
    ship `problem`, `approach` and `result` for every tile to render three
    lines. `id` is omitted too — `slug` is the public identifier.
    """

    class Meta:
        model = Project
        fields = ("slug", "title", "category", "summary", "description", "tech_stack")


class ProjectDetailSerializer(ProjectListSerializer):
    """Serialize a Project into the whole case study a detail page renders.

    Inherits the card fields so no field name is written twice; the detail
    payload is by construction a superset of the list payload. Nothing routes
    here yet — US-3.1-BE adds the retrieve endpoint.
    """

    class Meta(ProjectListSerializer.Meta):
        fields = (
            *ProjectListSerializer.Meta.fields,
            "problem",
            "approach",
            "result",
            "role",
            "year",
            "repo_url",
            "live_url",
            "image_url",
        )


class SkillSerializer(serializers.ModelSerializer):
    """Serialize a Skill into the shape the CORE SKILLS panel renders."""

    class Meta:
        model = Skill
        fields = ("id", "name", "years", "is_primary_focus")
