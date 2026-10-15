"""URL routes for the public portfolio site."""

from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("", views.home, name="home"),
    # `projects/grid/` MUST stay above the slug route: `grid` is itself a valid
    # slug, and Django takes the first pattern that matches, so swapping these
    # two would route the HTMX partial into the detail view.
    path("projects/grid/", views.project_grid, name="project-grid"),
    path("projects/<slug:slug>/", views.project_detail, name="project-detail"),
]
