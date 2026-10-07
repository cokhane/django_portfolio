"""URL routes for the portfolio API."""

from django.urls import path

from . import views

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("skills/", views.SkillListView.as_view(), name="skill-list"),
]
