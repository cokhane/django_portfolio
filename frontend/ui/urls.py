"""URL routes for the public portfolio site."""

from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/grid/", views.project_grid, name="project-grid"),
]
