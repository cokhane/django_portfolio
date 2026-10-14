"""URL routes for the portfolio API."""

from django.urls import path

from . import views

urlpatterns = [
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project-detail"),
    path("skills/", views.SkillListView.as_view(), name="skill-list"),
]
