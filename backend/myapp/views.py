"""Read-only API views backing the portfolio frontend."""

from rest_framework import generics

from .models import Project, Skill
from .serializers import ProjectListSerializer, SkillSerializer


class ProjectListView(generics.ListAPIView):
    """Every published portfolio project, ordered for display.

    The draft filter lives here rather than in the serializer: a serializer
    that tried to hide rows would emit `null` entries, where a filtered
    queryset simply returns a shorter list. Ordering comes from
    `Project.Meta.ordering` (`display_order`, then title).
    """

    queryset = Project.objects.filter(is_published=True)
    serializer_class = ProjectListSerializer


class SkillListView(generics.ListAPIView):
    """Every core skill, ordered for display."""

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
