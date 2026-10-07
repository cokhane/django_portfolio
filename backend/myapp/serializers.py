"""Serializers translating portfolio models into the API payload."""

from rest_framework import serializers

from .models import Project, Skill


class ProjectSerializer(serializers.ModelSerializer):
    """Serialize a Project into the shape the frontend template renders."""

    class Meta:
        model = Project
        fields = ("id", "title", "category", "description", "tech_stack")


class SkillSerializer(serializers.ModelSerializer):
    """Serialize a Skill into the shape the CORE SKILLS panel renders."""

    class Meta:
        model = Skill
        fields = ("id", "name")
