"""Read-only API views backing the portfolio frontend."""

from rest_framework import generics

from .models import Availability, Project, Skill
from .serializers import (
    AvailabilitySerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    SkillSerializer,
)

# The one published rule, read by every project view so a change to it reaches
# the grid and the detail page together. `slug` is derived from the title, so a
# rule applied to only the list would leave an unpublished case study invisible
# in the grid and readable by anyone who guesses its URL.
#
# DRF re-evaluates this per request — `GenericAPIView.get_queryset()` clones it
# with `.all()` — so the shared object is never iterated and never caches. Keep
# it that way: iterating it directly would fill a process-wide result cache.
PUBLISHED_PROJECTS = Project.objects.filter(is_published=True)


class ProjectListView(generics.ListAPIView):
    """Every published portfolio project, ordered for display.

    The draft filter lives in the queryset rather than in the serializer: a
    serializer that tried to hide rows would emit `null` entries, where a
    filtered queryset simply returns a shorter list. Ordering comes from
    `Project.Meta.ordering` (`display_order`, then title).
    """

    queryset = PUBLISHED_PROJECTS
    serializer_class = ProjectListSerializer


class ProjectDetailView(generics.RetrieveAPIView):
    """One published project at its own URL, as its whole case study.

    A draft is a `404` here, not a `403`, and that is the design rather than
    an accident: the published rule is a queryset filter, so `get_object()`
    never finds the row and a draft is indistinguishable from a slug that was
    never used. A permission check would instead find the row and then deny
    it — confirming to a visitor that something exists at that URL.
    """

    queryset = PUBLISHED_PROJECTS
    serializer_class = ProjectDetailSerializer
    lookup_field = "slug"


class SkillListView(generics.ListAPIView):
    """Every core skill, ordered for display."""

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class AvailabilityView(generics.RetrieveAPIView):
    """The author's availability as one object, at a URL with no lookup in it.

    `get_object()` replaces the usual queryset-plus-lookup because there is
    nothing to look up: the row is the singleton, and when it does not exist
    yet the view serves the model's unsaved default rather than a `404`. The
    hire-me panel therefore always has something to render, which is the state
    the database is in the day this ships.

    Only `get` is defined, so DRF answers every write `405` — the same way
    `ProjectDetailView` gets it, not a rule restated here.

    One consequence worth knowing: overriding `get_object()` skips
    `check_object_permissions()`. Nothing here is permissioned today; a
    permission class added later must be applied deliberately.
    """

    serializer_class = AvailabilitySerializer

    def get_object(self):
        return Availability.current()
