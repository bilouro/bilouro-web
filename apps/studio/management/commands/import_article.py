"""Import one article for studio.bilouro.com/artigos from a drafts folder.

    drafts/artigos/<slug>/article.pt.md
    drafts/artigos/<slug>/article.en.md

Each file: a front-matter block, then the Markdown body.

    ---
    title: Como acabar com as marcações por WhatsApp
    seo_title: ...            (optional, <title>)
    description: ...          (meta description; also the lede when no intro)
    intro: ...                (optional lede under the title)
    date: 2026-10-14          (PT file only)
    related: software-estudio-pilates   (PT file only; StudioSolutionPage slug)
    image: ../../studio-app/screens/03a-book-classes.png   (PT file only)
    ---
    ## Markdown body...

By default the article is saved as a DRAFT revision (not live) so it can be
reviewed in Wagtail. Pass --publish to make it live. The /artigos index is
created on first use and is only published together with an article.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from wagtail.images import get_image_model

from apps.studio.models import (
    StudioArticleIndexPage,
    StudioArticlePage,
    StudioHomePage,
    StudioSolutionPage,
)


def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise CommandError(f"{path}: missing front matter")
    _, fm, body = text.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return meta, body.strip() + "\n"


class Command(BaseCommand):
    help = "Import drafts/artigos/<slug>/article.{pt,en}.md into a StudioArticlePage (draft unless --publish)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--dir", default="drafts/artigos", help="Parent folder (default drafts/artigos)")
        parser.add_argument("--publish", action="store_true", help="Publish now (also publishes the /artigos index)")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report; write nothing")
        parser.add_argument("--go-live", help="Schedule: 'YYYY-MM-DD HH:MM' Europe/Lisbon. Sets the article date too; publishes the index now.")

    def _image(self, base: Path, ref: str):
        path = (base / ref).resolve()
        if not path.exists():
            raise CommandError(f"image not found: {path}")
        model = get_image_model()
        sha1 = hashlib.sha1(path.read_bytes()).hexdigest()  # noqa: S324 — dedup key
        found = model.objects.filter(title=path.name, file_hash=sha1).first()
        if found:
            return found
        with path.open("rb") as fh:
            img = model(title=path.name, file=ImageFile(fh, name=path.name), file_hash=sha1)
            img.save()
        return img

    def _index(self, publish: bool) -> StudioArticleIndexPage:
        idx = StudioArticleIndexPage.objects.first()
        if idx is None:
            home = StudioHomePage.objects.first()
            if not home:
                raise CommandError("No StudioHomePage")
            idx = StudioArticleIndexPage(
                title="Articles", title_pt="Artigos", slug="artigos", live=False,
                intro="<p>Practical guides for owners of Pilates studios, gyms, boxes and group-class studios: "
                      "bookings, waitlists, payments, invoicing and growing your membership.</p>",
                intro_pt="<p>Guias práticos para quem gere estúdios de Pilates, ginásios, boxes e estúdios de aulas "
                         "de grupo: marcações, lista de espera, pagamentos, faturação e crescer o número de sócios.</p>",
                seo_title="Guides for running Pilates studios, gyms and group classes | Bilouro Studio",
                seo_title_pt="Guias para gerir estúdios de Pilates, ginásios e aulas de grupo | Bilouro Studio",
                search_description="Practical articles on class booking, waitlists, no-shows, payments and invoicing for studios and gyms in Portugal.",
                search_description_pt="Artigos práticos sobre marcação de aulas, lista de espera, faltas, pagamentos e faturação para estúdios e ginásios em Portugal.",
            )
            home.add_child(instance=idx)
            idx.save_revision()
            self.stdout.write(self.style.SUCCESS("  + /artigos index created (draft)"))
        if publish and not idx.live:
            idx.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("  + /artigos index published"))
        return idx

    def handle(self, *args, **opts):
        base = Path(opts["dir"]) / opts["slug"]
        pt_meta, pt_body = parse(base / "article.pt.md")
        en_meta, en_body = parse(base / "article.en.md")
        for key in ("title", "description"):
            if not pt_meta.get(key) or not en_meta.get(key):
                raise CommandError(f"'{key}' missing in one of the languages")

        go_live = None
        if opts.get("go_live"):
            from zoneinfo import ZoneInfo
            go_live = dt.datetime.fromisoformat(opts["go_live"]).replace(tzinfo=ZoneInfo("Europe/Lisbon"))
        if opts["dry_run"]:
            self.stdout.write(f"{base} → /artigos/{opts['slug']}/ | PT: {pt_meta['title']} ({len(pt_body.split())} words) | "
                              f"EN: {en_meta['title']} ({len(en_body.split())} words) | related={pt_meta.get('related', '-')} | "
                              f"image={pt_meta.get('image', '-')} | go_live={go_live or '-'}")
            if pt_meta.get("image") and not (base / pt_meta["image"]).resolve().exists():
                raise CommandError(f"image not found: {pt_meta['image']}")
            self.stdout.write(self.style.WARNING("dry-run: nothing written"))
            return
        idx = self._index(opts["publish"] or bool(go_live))
        page = StudioArticlePage.objects.filter(slug=opts["slug"]).first()
        if page is None:
            page = StudioArticlePage(slug=opts["slug"], title=en_meta["title"], date=dt.date.today(), live=False)
            idx.add_child(instance=page)
            self.stdout.write(self.style.SUCCESS(f"  + created /artigos/{opts['slug']}/ (draft)"))

        page.title = en_meta["title"][:255]
        page.title_pt = pt_meta["title"][:255]
        page.seo_title = en_meta.get("seo_title", "")
        page.seo_title_pt = pt_meta.get("seo_title", "")
        page.search_description = en_meta["description"]
        page.search_description_pt = pt_meta["description"]
        page.intro = en_meta.get("intro") or en_meta["description"]
        page.intro_pt = pt_meta.get("intro") or pt_meta["description"]
        page.body_md, page.body_md_pt = en_body, pt_body
        if pt_meta.get("date"):
            page.date = dt.date.fromisoformat(pt_meta["date"])
        if pt_meta.get("related"):
            sol = StudioSolutionPage.objects.filter(slug=pt_meta["related"]).first()
            if not sol:
                raise CommandError(f"related solution '{pt_meta['related']}' not found")
            page.related_solution = sol
        if pt_meta.get("image"):
            page.image = self._image(base, pt_meta["image"])

        # Always build the revision from THIS object (it holds the imported content);
        # never re-fetch the DB row for a never-published page — its fields are empty.
        if go_live:
            page.date = go_live.date()
            page.go_live_at = go_live
        rev = page.save_revision()
        if opts["publish"] or go_live:
            rev.publish()  # future go_live_at → Wagtail schedules it
        if go_live:
            state = f"scheduled {go_live:%Y-%m-%d %H:%M} Lisbon"
        else:
            state = "LIVE" if opts["publish"] or page.live else "draft"
        words = len(pt_body.split())
        self.stdout.write(self.style.SUCCESS(f"imported → /artigos/{page.slug}/ [{state}] PT {words} words, {page.reading_minutes('pt')} min"))
