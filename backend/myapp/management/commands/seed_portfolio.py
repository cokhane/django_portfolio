"""Management command seeding the portfolio content.

The eight projects and four skills are transcribed from solutioning/case-studies.md;
nothing here is authored. An entry whose problem statement is still an unanswered
prompt seeds as a draft, so nothing half-written reaches the site.

Titles come from case-studies.md, not the BRD's shortlist table: that table still
carries a platform name the case studies anonymised away.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from myapp.models import Project, Skill

# The invented content this command used to load. Keyed on slug and name, it would
# otherwise survive a reseed untouched and linger beside the real shortlist.
SUPERSEDED_SLUGS = (
    "e-commerce-platform",
    "tech-blog-platform",
    "analytics-dashboard",
    "social-network",
    "task-manager",
    "portfolio-builder",
)
SUPERSEDED_SKILLS = (
    "Django / Python / FastApi",
    "React / Next.js / Tailwind CSS",
    "AWS / Digital Ocean / Azure",
    "Linux / Jenkins / Docker",
)

PROJECTS = (
    # 01 · Subscription Platform
    {
        "title": "Subscription Platform",
        "category": "PAYMENTS & COMMERCE",
        "year": "2025",
        "role": "Solo build",
        "tech_stack": [
            "FastAPI", "React", "PostgreSQL", "Celery", "RabbitMQ", "AWS", "Terraform",
        ],
        "summary": (
            "Built from scratch in two weeks. Opened a new revenue stream, now "
            "1,000+ orders a day."
        ),
        "problem": (
            "A commerce business had no recurring-revenue product and a two-week window "
            "to launch one. Nothing existed to build on: no billing, no subscription "
            "lifecycle, no way to take a payment that repeated."
        ),
        "approach": (
            "A backend on Repository, Unit of Work and Factory patterns, so the payment "
            "lifecycle stayed testable while it was written rather than after. A "
            "multi-cart system carrying two recurring plans and three one-time purchase "
            "types. The full lifecycle — retry logic, refunds, cancellation flows, "
            "notifications, audit logs. Async order processing on a queue so volume never "
            "blocked a checkout. Infrastructure as code, releases automated."
        ),
        "result": (
            "Delivered inside the deadline. It opened a new revenue stream and now "
            "processes 1,000+ orders a day."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": True,
    },
    # 02 · MSP Platform Overhaul
    {
        "title": "MSP Platform Overhaul",
        "category": "CLOUD & DATA",
        "year": "2020\u20132023",
        "role": "Team lead",
        "tech_stack": [
            "Django", "React", "MySQL", "AWS", "Terraform", "Ansible", "Jenkins",
        ],
        "summary": (
            "Rebuilt a monitoring platform end to end. The client went from 1 to 10 "
            "customers."
        ),
        "problem": "",
        "approach": (
            "Rebuilt the client-facing application and moved the backend onto Django, "
            "removing the performance bottleneck. Replaced a standalone admin dashboard "
            "with one served by the same app, eliminating an entire server. Designed "
            "cell-based per-client infrastructure isolation — each client getting a "
            "dedicated, independently managed stack — then abstracted that into "
            "parameterised modules, so a new client environment is provisioned in minutes "
            "from a single variable file with no manual infrastructure work."
        ),
        "result": (
            "The customer base grew from 1 to 10 and the team from 3 to 16. "
            "Infrastructure cost fell 67%."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 03 · AI Interview Platform
    {
        "title": "AI Interview Platform",
        "category": "AI PLATFORMS",
        "year": "2026",
        "role": "Architect",
        "tech_stack": [
            "Python 3.11 (aiohttp)", "React 19", "TypeScript", "AWS ECS Fargate",
            "Terraform", "Redis", "MongoDB",
        ],
        "summary": (
            "Real-time conversational AI conducting live video interviews with clinicians."
        ),
        "problem": "",
        "approach": (
            "An event-driven real-time platform, structured as a pure domain core behind "
            "thin vendor adapters, with module purity enforced in CI rather than by "
            "convention. Stateless sessions with distributed locking, so a mid-interview "
            "restart never drops a live participant. All media kept browser-to-vendor "
            "with audio relayed server-side — recording, credential isolation and "
            "barge-in authority with no dedicated media infrastructure. A two-tier model "
            "topology: a large model offline for guide synthesis, a fast one online for "
            "per-turn selection. Regulatory compliance built into the architecture rather "
            "than bolted on: a single screened egress path, pseudonymisation ahead of the "
            "model, consent enforced by construction."
        ),
        "result": (
            "21,832 raw signals distilled into 13 grounded interview questions at $0.13 "
            "per guide, with ungrounded questions rejected mechanically. A measured "
            "975 ms p95 latency budget. Delivered under a zero-suppression quality gate — "
            "1,864 tests at 100% enforced coverage."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 04 · Multi-tenant Pharma SaaS
    {
        "title": "Multi-tenant Pharma SaaS",
        "category": "MULTI-TENANT SAAS",
        "year": "2026",
        "role": "Architect",
        "tech_stack": [
            "Python 3.11", "AWS Lambda", "API Gateway", "EventBridge", "SQS",
            "MongoDB Atlas", "PostgreSQL", "Terraform",
        ],
        "summary": (
            "A competitive-intelligence platform serving four enterprise tenants in a "
            "regulated sector."
        ),
        "problem": "",
        "approach": (
            "A two-layer platform separating a shared data plane from a per-tenant read "
            "lens: intelligence is collected once per subject into a common lake, then "
            "personalised per customer at read time — so collection cost scales with "
            "subjects rather than customers, and no tenant-specific copy of a record "
            "exists anywhere. Database-per-tenant isolation for all client-private state, "
            "making cross-tenant leakage structurally impossible rather than a "
            "query-filter convention. Event-driven fan-out with bulkhead isolation, so "
            "one source's outage cannot stall the rest."
        ),
        "result": (
            "308 independently deployable functions across four environments, built once "
            "and promoted everywhere as immutable images, with blue/green canary deploys "
            "and automatic rollback."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 05 · Autonomous Agent Platform
    {
        "title": "Autonomous Agent Platform",
        "category": "AI PLATFORMS",
        "year": "2026",
        "role": "Architect",
        "tech_stack": [
            "Headless agent runners", "Python", "Jira REST API", "GitHub Actions",
            "Terraform",
        ],
        "summary": (
            "A fleet of coding agents that take tickets end to end — and provably cannot "
            "merge their own work."
        ),
        "problem": "",
        "approach": (
            "A production agent platform working tickets end to end — queue selection, "
            "repo routing, implementation, signed commits, pull request — across a "
            "30-runner fleet spanning 10 projects and ~15 repositories. A guardrail model "
            "for unattended agents holding live credentials: a prompt-level operating "
            "charter, forbidden-path push hooks, and queue scoping by assignee, including "
            "blocking agents from selecting their own reviewers. Infrastructure work runs "
            "under a deliberate plan-only policy — it writes infrastructure code, never "
            "applies it — separating authorship from deployment authority."
        ),
        "result": (
            "Every agent pull request passes a two-agent quality gate and a human merge. "
            "No autonomous merge path exists."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 06 · Learning Platform Rebuild
    {
        "title": "Learning Platform Rebuild",
        "category": "PAYMENTS & COMMERCE",
        "year": "2025",
        "role": "Full-stack",
        "tech_stack": ["FastAPI", "PostgreSQL", "Selenium", "pytest"],
        "summary": (
            "Rebuilt the billing engine. Daily payment authorisation rates rose "
            "40\u201360%."
        ),
        "problem": "",
        "approach": (
            "Rebuilt the rebilling engine from scratch. Re-architected the product from "
            "single-lesson to multi-lesson support, enabling horizontal scalability and a "
            "wider catalogue. Rebuilt the authentication system, resolving a bug that was "
            "blocking 20% of active users from logging in. Built the admin panel that cut "
            "customer-support response time. Unit, integration and end-to-end coverage "
            "across rebilling, auth and lessons, blocking production regressions."
        ),
        "result": "Daily payment authorisation rates increased 40\u201360%.",
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 07 · Real-Time Monitoring System
    {
        "title": "Real-Time Monitoring System",
        "category": "CLOUD & DATA",
        "year": "2025",
        "role": "Full-stack",
        "tech_stack": ["FastAPI", "React", "WebSocket", "Ansible", "EC2"],
        "summary": "Replaced manual attendance tracking. Scheduling overhead fell ~90%.",
        "problem": "",
        "approach": (
            "A monitoring application integrating video-call platforms to track "
            "attendance, punctuality and call duration in real time. A WebSocket backend "
            "delivering instant push notifications to a dashboard and chat alerts, "
            "removing manual monitoring entirely. A KPI dashboard surfacing attendance "
            "patterns and performance metrics for management. Infrastructure provisioned "
            "with configuration management for repeatable deployment."
        ),
        "result": (
            "Booking workflows automated, cutting scheduling overhead by roughly 90%, and "
            "support escalations reduced across the platform."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
    # 08 · AI Medical Records Platform
    {
        "title": "AI Medical Records Platform",
        "category": "AI PLATFORMS",
        "year": "2025",
        "role": "Architect",
        "tech_stack": ["Django", "React", "LLM API", "Payload CMS", "ETL", "GCP"],
        "summary": (
            "LLM extraction from PDF medical records, eliminating manual data entry for "
            "doctors."
        ),
        "problem": (
            "Doctors were manually re-typing patient data from PDF medical records into a "
            "system before it could be used."
        ),
        "approach": (
            "An ETL pipeline for automated PDF ingestion, with LLM-powered extraction "
            "pulling structured data out of unstructured records and generating reports "
            "from it. A no-code report builder letting non-technical admins customise "
            "report templates without engineering support. A migration mapping and "
            "transforming existing commerce records into structured medical record "
            "formats. Deployed on a high-availability cloud stack across two zones."
        ),
        "result": (
            "Manual data entry eliminated for doctors. Unstructured PDF records became "
            "queryable patient data."
        ),
        "repo_url": "",
        "live_url": "",
        "image_url": "",
        "is_published": False,
    },
)

# The CORE SKILLS panel from mockup screen 02 (BRD A12, confirmed 2026-10-13).
SKILLS = (
    {"name": "AI / LLM Platforms", "years": 2, "is_primary_focus": True},
    {"name": "Multi-tenant Architecture", "years": 6, "is_primary_focus": True},
    {"name": "Python / Django / FastAPI", "years": 9, "is_primary_focus": False},
    {"name": "AWS / Terraform", "years": 7, "is_primary_focus": False},
)


def project_defaults(entry, order):
    """The row one case study writes.

    `description` is the card line the grid still renders, and `summary` is the
    case study's own one-line card text — the same sentence by design, so it is
    derived here rather than transcribed twice. US-3.4-FE retires it.
    """
    return {**entry, "description": entry["summary"], "display_order": order}


class Command(BaseCommand):
    """Load the portfolio content that used to be hardcoded in the template."""

    help = "Seed the database with the portfolio's projects and skills."

    @transaction.atomic
    def handle(self, *args, **options):
        Project.objects.filter(slug__in=SUPERSEDED_SLUGS).delete()
        Skill.objects.filter(name__in=SUPERSEDED_SKILLS).delete()

        for order, entry in enumerate(PROJECTS):
            Project.objects.update_or_create(
                slug=slugify(entry["title"]),
                defaults=project_defaults(entry, order),
            )

        for order, skill in enumerate(SKILLS):
            Skill.objects.update_or_create(
                name=skill["name"], defaults={**skill, "display_order": order}
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PROJECTS)} projects and {len(SKILLS)} skills."
            )
        )
