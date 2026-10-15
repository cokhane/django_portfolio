"""Content models for the portfolio: projects, core skills and availability."""

from django.db import models

# The only primary key an Availability row may hold. Named once here and read by
# the pk's default, the check constraint and `current()`, so the three agree by
# construction rather than by three authors remembering the same literal.
SINGLETON_PK = 1


class Project(models.Model):
    """A portfolio piece rendered as a card in the projects grid."""

    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=40)
    description = models.TextField()
    tech_stack = models.JSONField(
        default=list,
        help_text="Display-only tag names, e.g. ['Django', 'React'].",
    )
    summary = models.TextField(blank=True, default="")
    problem = models.TextField(blank=True, default="")
    approach = models.TextField(blank=True, default="")
    result = models.TextField(blank=True, default="")
    role = models.CharField(max_length=40, blank=True, default="")
    year = models.CharField(max_length=12, blank=True, default="")
    repo_url = models.URLField(blank=True, default="")
    live_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "title")

    def __str__(self):
        return self.title


class Skill(models.Model):
    """One line in the CORE SKILLS panel."""

    name = models.CharField(max_length=120, unique=True)
    years = models.PositiveSmallIntegerField(
        default=0,
        help_text="Whole years of experience, set by the author. 0 is a real value.",
    )
    is_primary_focus = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class Engagement(models.Model):
    """One "what I take on" card: a label and the line under it.

    The author's own words, not template text: renaming a card must not need a
    deploy (BRD F-11). Rows rather than numbered fields on `Availability`
    because a card is a label AND a body, so three cards as fields would be six
    scalars in a repeating group — and a fourth card would be a migration.
    """

    label = models.CharField(max_length=40, unique=True)
    body = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "label")

    def __str__(self):
        return self.label


class Availability(models.Model):
    """The author's one availability statement. BRD F-7.

    A singleton enforced in the database, not in `save()`: the primary key
    defaults to `SINGLETON_PK` and a check constraint refuses any other value,
    so EVERY write path lands on the one row or raises. A rule written into
    `save()` instead would be skipped by `bulk_create()` and by `loaddata`,
    which never call it -- the table would then quietly hold two rows and the
    endpoint would have to choose between them.

    Editing through admin loads the row first, so it UPDATEs as usual.
    `AvailabilityModelTests` walks the write paths one by one and is the list;
    it is not repeated here, where it would go stale unnoticed.

    No rate field exists and none may be added (BRD G7); `tests.py` pins the
    field names as an exact set so adding one cannot pass review unnoticed.
    """

    class State(models.TextChoices):
        """What the author is currently saying about taking work."""

        UNSTATED = "unstated", "Unstated"
        OPEN = "open", "Open"
        BOOKED = "booked", "Booked"

    # Explicit rather than the usual AutoField, and the reason is measured: the
    # constraint alone already refuses a second row, but SQLite's AUTOINCREMENT
    # never reuses a key. So with an AutoField, once the author DELETES the row
    # -- which admin allows, and is how they go back to saying nothing -- the
    # next insert is offered pk 2, the constraint refuses it, and availability
    # could never be stated again. A pinned default always offers SINGLETON_PK,
    # so re-creating works. `test_the_row_can_be_recreated_after_deletion`.
    id = models.PositiveSmallIntegerField(
        primary_key=True, default=SINGLETON_PK, editable=False
    )
    state = models.CharField(
        max_length=12, choices=State.choices, default=State.UNSTATED
    )
    available_from = models.DateField(
        null=True,
        blank=True,
        help_text="Pick the 1st of the month; the site renders the month only.",
    )

    class Meta:
        verbose_name_plural = "availability"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(id=SINGLETON_PK),
                name="availability_is_a_singleton",
            ),
        )

    def __str__(self):
        return "Availability"

    @classmethod
    def current(cls):
        """The one row, or an unsaved default when nothing has been filled in.

        The unsaved instance is what keeps the endpoint off a 404 before the
        author has typed anything, and it costs no write on a read path. Its
        values are the field defaults, so "empty" is described in one place --
        the model -- rather than by a second constant beside the serializer.
        """
        return cls.objects.filter(pk=SINGLETON_PK).first() or cls()

    @property
    def engagements(self):
        """Every card, ordered for display; read by the nested serializer.

        A plain query rather than a reverse FK: with exactly one availability,
        a foreign key would point every row at the same parent and would have
        to be filled in before an unsaved default could carry any cards.
        """
        return Engagement.objects.all()
