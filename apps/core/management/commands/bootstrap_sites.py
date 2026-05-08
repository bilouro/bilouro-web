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
from apps.tech.models import BlogIndexPage


SITE_SPECS = [
    {
        "host_local": "www.localhost",
        "host_prod": "www.bilouro.com",
        "is_default": True,
        "page_model": HomePage,
        "page_data": {
            "title": "Victor H. Bilouro",
            "slug": "home",
            "intro": "<p>Engenheiro, Tech Lead, escritor. Notas, projetos e leitura.</p>",
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
            "intro": "<p>Notas técnicas, arquitectura e leadership hands-on.</p>",
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
            "intro": "<p>Livros publicados.</p>",
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

            # Create or update Site
            site, created = Site.objects.update_or_create(
                hostname=hostname,
                defaults={
                    "port": 80,
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
                headline="Hands-on Tech Lead & Solutions Architect",
                bio="<p>22+ years delivering and leading engineering teams. Currently in Porto, Portugal.</p>",
                skills="<p>Python · Java · AWS · GenAI · Postgres · Architecture</p>",
                contact_links=(
                    "<p>"
                    "<a href='https://www.linkedin.com/in/bilouro' target='_blank'>LinkedIn</a> · "
                    "<a href='https://github.com/bilouro' target='_blank'>GitHub</a>"
                    "</p>"
                ),
            )
            home.add_child(instance=about)
            about.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("  + AboutPage created"))

        catalog = BookCatalogPage.objects.first()
        if catalog and not BookPage.objects.exists():
            book = BookPage(
                title="Jesus, o Líder",
                slug="jesus-o-lider",
                subtitle="Reflexões sobre liderança a partir do exemplo de Jesus",
                language="pt",
                description=(
                    "<p>Reflexões semanais sobre liderança moderna a partir de "
                    "passagens dos Evangelhos. Aplicação prática para gestores, "
                    "tech leads e fundadores.</p>"
                ),
                price_eur=0,
                buy_url="",
            )
            catalog.add_child(instance=book)
            book.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("  + BookPage 'Jesus, o Líder' created"))

        self.stdout.write(self.style.SUCCESS("\nbootstrap_sites complete."))
