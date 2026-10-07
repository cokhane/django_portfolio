"""URL configuration for the portfolio API service.

This project is API-only; the public site is rendered by the sibling
`frontend` project, which consumes these endpoints over HTTP.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("myapp.urls")),
]
