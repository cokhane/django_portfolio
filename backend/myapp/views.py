"""Read-only API views backing the portfolio frontend."""

from rest_framework import generics

from .models import Project, Skill
from .serializers import ProjectListSerializer, SkillSerializer


class ProjectListView(generics.ListAPIView):
    """Every portfolio project, ordered for display."""

    queryset = Project.objects.all()
    serializer_class = ProjectListSerializer


class SkillListView(generics.ListAPIView):
    """Every core skill, ordered for display."""

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
