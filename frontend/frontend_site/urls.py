"""URL configuration for the portfolio frontend."""

from django.urls import include, path

urlpatterns = [
    path("", include("ui.urls")),
]
