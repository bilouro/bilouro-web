"""Idempotent bootstrap: create the 3 Wagtail Sites + their root pages.

Sites:
    - www.bilouro.com   → HomePage  ("home")
    - tech.bilouro.com  → BlogIndexPage  ("tech")
    - books.bilouro.com → BookCatalogPage  ("books")

Local hostnames default to www.localhost / tech.localhost / books.localhost
unless --prod is passed (then uses production hostnames).
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from apps.autoral.models import AboutPage, HomePage
from apps.shop.models import BookCatalogPage, BookPage
from apps.tech.models import BlogIndexPage, ProjectIndexPage, ProjectPage


SITE_SPECS = [
    {
        "host_local": "www.localhost",
        "host_prod": "www.bilouro.com",
        "is_default": True,
        "page_model": HomePage,
        "page_data": {
            "title": "Victor H. Bilouro",
            "slug": "home",
            "intro": "<p>Engineer, Tech Lead, writer. Notes, projects, and reading.</p>",
            "intro_pt": "<p>Engenheiro, Tech Lead, escritor. Notas, projetos e leitura.</p>",
        },
    },
    {
        "host_local": "tech.localhost",
        "host_prod": "tech.bilouro.com",
        "is_default": False,
        "page_model": BlogIndexPage,
        "page_data": {
            "title": "tech.bilouro",
            "slug": "tech",
            "intro": "<p>Technical notes, architecture, and hands-on leadership.</p>",
            "intro_pt": "<p>Notas técnicas, arquitectura e leadership hands-on.</p>",
        },
    },
    {
        "host_local": "books.localhost",
        "host_prod": "books.bilouro.com",
        "is_default": False,
        "page_model": BookCatalogPage,
        "page_data": {
            "title": "Books",
            "slug": "books",
            "intro": "<p>Published books.</p>",
            "intro_pt": "<p>Livros publicados.</p>",
        },
    },
]


class Command(BaseCommand):
    help = "Create Wagtail Sites + root pages (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prod",
            action="store_true",
            help="Use production hostnames (www.bilouro.com etc.)",
        )

    def handle(self, *args, **opts):
        root = Page.objects.filter(depth=1).first()
        if not root:
            self.stderr.write("No Wagtail root page found. Did you run migrate?")
            return

        # Remove the default Wagtail "Welcome to your new Wagtail site!" page if present
        default_welcome = Page.objects.filter(slug="home", depth=2).first()
        if default_welcome and not isinstance(default_welcome.specific, HomePage):
            self.stdout.write(f"Removing default Wagtail welcome page: {default_welcome}")
            default_welcome.delete()

        # Remove the default Site (will be replaced)
        Site.objects.filter(hostname="localhost").delete()

        for spec in SITE_SPECS:
            hostname = spec["host_prod"] if opts["prod"] else spec["host_local"]
            slug = spec["page_data"]["slug"]

            # Create or get the page
            page = spec["page_model"].objects.filter(slug=slug).first()
            if not page:
                page = spec["page_model"](**spec["page_data"])
                root.add_child(instance=page)
                page.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"  + page {slug}: {page.title}"))
            else:
                self.stdout.write(f"  ~ page {slug} exists")

            # Create or update Site — port 443 in prod (HTTPS), 80 locally
            port = 443 if opts["prod"] else 80
            site, created = Site.objects.update_or_create(
                hostname=hostname,
                defaults={
                    "port": port,
                    "root_page": page,
                    "is_default_site": spec["is_default"],
                    "site_name": spec["page_data"]["title"],
                },
            )
            verb = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  + site {hostname} → {slug} ({verb})"))

        # Sub-pages: AboutPage under HomePage; sample BookPage under BookCatalogPage
        home = HomePage.objects.first()
        if home and not AboutPage.objects.exists():
            about = AboutPage(
                title="About",
                slug="about",
                headline=(
                    "Hands-on Tech Lead & Solutions Architect · Python · Java · AWS · "
                    "Gen-AI · 22+ yrs Delivering & Leading Engineering Teams"
                ),
                bio=(
                    "<p>I code and I lead — and I'm good at making each one strengthen the other.</p>"
                    "<p>22+ years in engineering, the last 15 leading teams and products across "
                    "logistics, insurance, retail and financial services. Never stopped being "
                    "hands-on: ~200 commits across 14 new repos last year, including production "
                    "Gen-AI agent stacks for real small businesses.</p>"
                    "<p>Where I operate best: the seam between tech strategy and execution.</p>"
                ),
                skills=(
                    "<p><strong>Architect and build:</strong> Python (Django, Flask, SQLAlchemy), "
                    "Java (Spring Boot), Kafka, Postgres/Oracle/MySQL, Docker/Kubernetes, AWS "
                    "(Lambda, ECS Fargate, RDS, EKS), Pulumi/Terraform.</p>"
                    "<p><strong>Modernize legacy:</strong> strangler pattern, data-model redesign, "
                    "platform migrations (OpenShift → AWS EKS).</p>"
                    "<p><strong>Release engineering at scale:</strong> Control-M, Jenkins, XL "
                    "Deploy, XL Release on heterogeneous Java/C/Perl/Shell stacks — automated "
                    "end-to-end.</p>"
                    "<p><strong>Applied AI:</strong> voice + email agents in production (Vapi + "
                    "Vonage + OpenAI · Gmail + OpenAI).</p>"
                    "<p><strong>Lead teams:</strong> Scrum, Kanban, SAFe, Lean, Management 3.0. "
                    "Coach leads and engineers; build psychologically safe, data-driven cultures.</p>"
                ),
                experience=(
                    "<p><strong>Currently:</strong> Release Manager on an 80+ engineer program, "
                    "where I built (solo, in Python) the full automation stack we run releases on "
                    "— Control-M orchestration, Jira/Confluence integrations, paramiko-based Linux "
                    "ops, a Sybase QA framework, and a bash daemon framework.</p>"
                    "<p><strong>Recent (Kuehne+Nagel, 2022–2025):</strong> led modernization of a "
                    "mission-critical Customer Master Data monolith into Java/Spring microservices "
                    "with Elasticsearch and Angular, using a strangler layer for legacy consumers "
                    "— while migrating from OpenShift to AWS EKS. Recognized internally as a "
                    "modernization success case.</p>"
                    "<p><strong>Earlier:</strong> Leroy Merlin (Ytech), Azul Seguros, Bradesco "
                    "Seguros, Natixis. CI/CD, containerization, cloud adoption for order-management "
                    "and insurance products.</p>"
                    "<p><strong>Certifications:</strong> PMP · CSPO · CSM · Kanban · "
                    "Management 3.0 · AWS Cloud Practitioner · SCJP.</p>"
                    "<p><strong>Languages:</strong> Portuguese (native), English (C1), "
                    "Spanish (B1).</p>"
                    "<p><strong>Based in Porto, Portugal.</strong> Open to remote or on-site in PT.</p>"
                ),
                contact_links=(
                    "<p>"
                    "<a href='https://www.linkedin.com/in/bilouro' target='_blank' rel='noopener'>LinkedIn</a> · "
                    "<a href='https://github.com/bilouro' target='_blank' rel='noopener'>GitHub</a> · "
                    "<a href='mailto:hello@bilouro.com'>hello@bilouro.com</a>"
                    "</p>"
                ),
            )
            home.add_child(instance=about)
            about.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("  + AboutPage created"))

        catalog = BookCatalogPage.objects.first()
        if catalog:
            books = [
                {
                    "title": "Jesus, o Líder",
                    "slug": "jesus-o-lider",
                    "subtitle": "Reflexões sobre liderança a partir do exemplo de Jesus",
                    "language": "pt",
                    "description": (
                        "<p>Reflexões semanais sobre liderança moderna à luz do exemplo "
                        "de Jesus. Aplicação prática para gestores, tech leads e fundadores.</p>"
                        "<p>Os posts pré-lançamento abaixo são parte do percurso até o livro.</p>"
                    ),
                },
                {
                    "title": "Jesus, the Leader",
                    "slug": "jesus-the-leader",
                    "subtitle": "Reflections on modern leadership through Jesus' example",
                    "language": "en",
                    "description": (
                        "<p>Weekly reflections on modern leadership, drawn from passages of "
                        "the Gospels. Practical application for managers, tech leads and founders.</p>"
                        "<p>The pre-launch posts below are part of the journey to the book.</p>"
                    ),
                },
            ]
            for spec in books:
                if BookPage.objects.filter(slug=spec["slug"]).exists():
                    self.stdout.write(f"  ~ BookPage {spec['slug']} exists")
                    continue
                book = BookPage(
                    title=spec["title"],
                    slug=spec["slug"],
                    subtitle=spec["subtitle"],
                    language=spec["language"],
                    description=spec["description"],
                    price_eur=0,
                    coming_soon=True,
                    buy_url="",
                )
                catalog.add_child(instance=book)
                book.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"  + BookPage '{spec['title']}' created"))

        # Tech projects index + projects
        tech_index = BlogIndexPage.objects.first()
        if tech_index:
            project_index = ProjectIndexPage.objects.filter(slug="projects").first()
            if not project_index:
                project_index = ProjectIndexPage(
                    title="Projects",
                    slug="projects",
                    intro=(
                        "<p>Selected work — open-source, professional, and side projects "
                        "across 20+ years. Public repos linked; private/work projects "
                        "described without sensitive details.</p>"
                    ),
                )
                tech_index.add_child(instance=project_index)
                project_index.save_revision().publish()
                self.stdout.write(self.style.SUCCESS("  + ProjectIndexPage created"))

            projects = [
                {
                    "title": "Customer Master Data — Strangler Migration",
                    "slug": "kuehne-nagel-cmd-modernization",
                    "kind": "work", "period": "2022-2025",
                    "summary": "Modernized a mission-critical Customer Master Data monolith into Java/Spring microservices via the strangler pattern, while migrating from OpenShift to AWS EKS. Zero ticket from legacy consumers.",
                    "description": "<p>Three-and-a-half years inheriting a mission-critical CMD monolith and a plan: move to microservices without stopping global operations. Strangler pattern with adapter layer in front of the legacy API speaking the old contract verbatim, feature-by-feature routing (not endpoint-by-endpoint), parallel-write window during data migration with divergence metrics. PL/SQL migration AND rollback scripts from day one.</p><p>Result: monolith shrunk, team got an evolvable platform, legacy consumers never filed a ticket.</p>",
                    "tech_stack": "Java, Spring Boot, Kafka, PostgreSQL, Oracle, Elasticsearch, AWS EKS, OpenShift, Pulumi",
                    "sort_order": 10,
                },
                {
                    "title": "Voice Agent for SMBs (Pilates studios)",
                    "slug": "voice-agent-smb",
                    "kind": "personal", "period": "2024-2026",
                    "summary": "Production voice agent on real phone numbers for two pilates studios — Vapi + Vonage + OpenAI. Schedules, reschedules, takes intake, escalates to human.",
                    "description": "<p>Built end-to-end on AWS with Pulumi-managed serverless infra. Custom dialog flow, integration with the studios' booking systems, voicemail-grade reliability. Detailed write-up across multiple LinkedIn posts (see blog).</p>",
                    "tech_stack": "Python, OpenAI, Vapi, Vonage, AWS Lambda, RDS, Pulumi",
                    "sort_order": 20,
                },
                {
                    "title": "Email Agent — IMAP/SMTP + LLM",
                    "slug": "email-agent",
                    "kind": "personal", "period": "2024-2026",
                    "summary": "Production email agent that reads/replies via Gmail IMAP/SMTP, classifies intent, drafts replies, and pulls context from internal data.",
                    "description": "<p>Companion to the voice agent. Runs in the same AWS infrastructure. Used for SMB-scale automation where receptionist tier costs are prohibitive.</p>",
                    "tech_stack": "Python, OpenAI, IMAP, SMTP, AWS Lambda",
                    "sort_order": 30,
                },
                {
                    "title": "Release Engineering Automation Stack",
                    "slug": "release-automation-stack",
                    "kind": "work", "period": "2025-current",
                    "summary": "Solo-built (in Python) a full automation stack for an 80+ engineer release program: Control-M orchestration, Jira/Confluence integrations, paramiko-based Linux ops, Sybase QA framework, bash daemon framework.",
                    "description": "<p>Currently used to run weekly releases across heterogeneous Java/C/Perl/Shell stacks. End-to-end automated.</p>",
                    "tech_stack": "Python, paramiko, Control-M, Jenkins, XL Deploy, XL Release, Sybase, Jira, Confluence",
                    "sort_order": 40,
                },
                {
                    "title": "bilouro-web — this site",
                    "slug": "bilouro-web",
                    "kind": "personal", "period": "2026",
                    "summary": "Wagtail multi-site (3 subdomains) on AWS Lightsail with nginx, Postgres, gunicorn, Certbot, S3 media. Migrated from App Runner mid-build for cost + simplicity.",
                    "description": "<p>Single Wagtail project serving 3 subdomains via the multi-site feature. Apex 301-redirected to www. Postgres 16 local on the VM, weekly pg_dump → S3.</p>",
                    "tech_stack": "Python, Django, Wagtail, Postgres, nginx, AWS Lightsail, S3, Terraform",
                    "github_url": "https://github.com/bilouro/bilouro-web",
                    "sort_order": 60,
                },
                {
                    "title": "nodejs-file-reading — positional file ETL",
                    "slug": "nodejs-file-reading",
                    "kind": "oss", "period": "2021",
                    "summary": "Node.js engine for parsing fixed-width text files with hierarchical line types (parent/child) and persisting to Postgres (Sequelize) or MongoDB (Mongoose).",
                    "description": "<p>Solves the classic legacy-interchange problem: positional files where each line's first N characters select a different schema (header / lines / events) and records form a tree. Format is declared as a 'file mapping' (discriminator + per-line attributes), so adding a new format is config, not code.</p><p>Includes 4 versions (m41/m51/m80/m90) of a real banking/insurance message family, Postgres and MongoDB persistence variants, full Jest coverage on the core parser.</p>",
                    "tech_stack": "Node.js, Sequelize, PostgreSQL, Mongoose, MongoDB, Jest, Moment",
                    "github_url": "https://github.com/bilouro/nodejs-file-reading",
                    "sort_order": 65,
                },
                {
                    "title": "FlaskProject — Books REST API (reference)",
                    "slug": "flask-books-api",
                    "kind": "oss", "period": "2024",
                    "summary": "Reference Flask + SQLAlchemy + Postgres + Alembic implementation of a Books CRUD API. Clean separation: routes / repository / models. OpenAPI docs, tests, Docker.",
                    "description": "<p>A teaching-grade Flask REST API: routes, repository, SQLAlchemy models, environment-based config (dev/test/prod), Alembic migrations, OpenAPI/Swagger UI, JSON error handling, unit + functional tests, ready-to-run docker-compose with Postgres.</p><p>Useful starting point for new Flask backends — the structural choices are deliberate and documented in the README.</p>",
                    "tech_stack": "Python, Flask, SQLAlchemy, PostgreSQL, Alembic, OpenAPI, Docker, pytest",
                    "github_url": "https://github.com/bilouro/FlaskProject",
                    "sort_order": 67,
                },
                {
                    "title": "cookbook — personal recipe playground",
                    "slug": "cookbook",
                    "kind": "oss", "period": "ongoing",
                    "summary": "Long-running personal repo of code recipes, snippets and experiments — AWS, Python, Django, integrations.",
                    "description": "<p>Public dump of useful patterns I've found or built over the years. Updated when something interesting comes up.</p>",
                    "tech_stack": "Python, Django, AWS, misc",
                    "github_url": "https://github.com/bilouro/cookbook",
                    "sort_order": 70,
                },
                {
                    "title": "querysetget — auto-expose Django QuerySet via REST",
                    "slug": "querysetget",
                    "kind": "oss", "period": "2017",
                    "summary": "A small library that auto-exposes Django QuerySet API via GET/querystring of all models in a project — REST-like format, zero config.",
                    "description": "<p>Useful for quick admin-side data exploration without writing per-model views.</p>",
                    "tech_stack": "Python, Django",
                    "github_url": "https://github.com/bilouro/querysetget",
                    "sort_order": 80,
                },
                {
                    "title": "sgsb — Beauty Salon SaaS",
                    "slug": "sgsb",
                    "kind": "oss", "period": "2014",
                    "summary": "Django application to manage beauty salons and hair salons — appointments, services, customers.",
                    "description": "<p>Older Django project; published to GitHub for reference.</p>",
                    "tech_stack": "Python, Django",
                    "github_url": "https://github.com/bilouro/sgsb",
                    "sort_order": 90,
                },
                {
                    "title": "SGUI — Church management system",
                    "slug": "sgui",
                    "kind": "oss", "period": "2014",
                    "summary": "Sistema de Gestão Unificado de Igrejas — Django app to administer church operations.",
                    "description": "<p>Multi-tenant Django app for church management.</p>",
                    "tech_stack": "Python, Django",
                    "github_url": "https://github.com/bilouro/SGUI",
                    "sort_order": 100,
                },
                {
                    "title": "Arduino Coding Dojo Timer",
                    "slug": "arduino-codingdojo",
                    "kind": "oss", "period": "2012",
                    "summary": "A simple Arduino gadget to control the Coding Dojo timebox.",
                    "tech_stack": "Arduino, C++",
                    "github_url": "https://github.com/bilouro/arduino_codingdojo",
                    "sort_order": 110,
                },
                {
                    "title": "GSoC 2008 — FreeBSD",
                    "slug": "gsoc-2008-freebsd",
                    "kind": "oss", "period": "2008",
                    "summary": "Google Summer of Code 2008 contribution to FreeBSD — TCP test tooling. Public reference at wiki.freebsd.org/SummerOfCode2008.",
                    "tech_stack": "Python, FreeBSD, TCP/IP",
                    "github_url": "https://github.com/bilouro/tcptest",
                    "live_url": "https://wiki.freebsd.org/SummerOfCode2008",
                    "sort_order": 120,
                },
            ]
            for spec in projects:
                if ProjectPage.objects.filter(slug=spec["slug"]).exists():
                    continue
                p = ProjectPage(**spec)
                project_index.add_child(instance=p)
                p.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"  + Project '{spec['title'][:50]}'"))

        self.stdout.write(self.style.SUCCESS("\nbootstrap_sites complete."))
