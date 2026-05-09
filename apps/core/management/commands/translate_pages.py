"""Translate Wagtail Page content via OpenAI Responses API.

Per-field PT scaffolding: each translatable model has fields like `intro` and
`intro_pt`. This command reads the EN fields, sends them to OpenAI with the
configured prompt_id, and writes the result to the matching `_pt` fields.

Skips:
 - BookPostPage (book posts stay in their original language per project rules)
 - Pages whose `_pt` fields are already populated unless --force is passed

Usage:
    python manage.py translate_pages
    python manage.py translate_pages --slug=home
    python manage.py translate_pages --dry-run
    python manage.py translate_pages --force --slug=home

Required env (or settings):
    OPENAI_API_KEY
    OPENAI_TRANSLATION_PROMPT_ID  (a pmpt_... ID from platform.openai.com/prompts)
    OPENAI_TRANSLATION_PROMPT_VERSION  (default: "1")
"""
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Page

# Per-model: page_type label + list of (source_field, target_pt_field) pairs.
TRANSLATABLE = {
    "HomePage": ("home", [("intro", "intro_pt"), ("body", "body_pt")]),
    "AboutPage": (
        "about",
        [
            ("title", "title_pt"),
            ("headline", "headline_pt"),
            ("bio", "bio_pt"),
            ("skills", "skills_pt"),
            ("experience", "experience_pt"),
            ("contact_links", "contact_links_pt"),
        ],
    ),
    "BlogIndexPage": ("blog_index", [("intro", "intro_pt")]),
    "BlogPostPage": (
        "blog_post",
        [("title", "title_pt"), ("intro", "intro_pt"), ("body_md", "body_md_pt")],
    ),
    "ProjectIndexPage": ("project_index", [("intro", "intro_pt")]),
    "ProjectPage": (
        "project",
        [("title", "title_pt"), ("summary", "summary_pt"), ("description", "description_pt")],
    ),
    "BookCatalogPage": ("book_catalog", [("title", "title_pt"), ("intro", "intro_pt")]),
    "BookPage": (
        "book",
        [("subtitle", "subtitle_pt"), ("description", "description_pt")],  # NOT title — book name same in both
    ),
    # BookPostPage: NOT translated.
}


def call_openai(api_key: str, prompt_id: str, prompt_version: str, payload: dict) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        prompt={"id": prompt_id, "version": prompt_version},
        input=json.dumps(payload, ensure_ascii=False),
    )
    text = None
    if hasattr(resp, "output_text") and resp.output_text:
        text = resp.output_text
    else:
        for it in getattr(resp, "output", []) or []:
            for c in getattr(it, "content", []) or []:
                if hasattr(c, "text"):
                    text = c.text
                    break
            if text:
                break
    if not text:
        raise RuntimeError("Empty OpenAI response")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


class Command(BaseCommand):
    help = "Translate Wagtail page content into _pt fields via OpenAI."

    def add_arguments(self, parser):
        parser.add_argument("--slug", help="Translate only this page slug")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true", help="Overwrite even if _pt is already filled")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts):
        api_key = os.getenv("OPENAI_API_KEY")
        prompt_id = os.getenv("OPENAI_TRANSLATION_PROMPT_ID")
        prompt_version = os.getenv("OPENAI_TRANSLATION_PROMPT_VERSION", "1")
        if not api_key or not prompt_id:
            raise CommandError("Need OPENAI_API_KEY and OPENAI_TRANSLATION_PROMPT_ID")

        qs = Page.objects.live()
        if opts["slug"]:
            qs = qs.filter(slug=opts["slug"])

        pages = []
        for p in qs:
            spec = p.specific
            if type(spec).__name__ in TRANSLATABLE:
                pages.append(spec)

        if opts["limit"]:
            pages = pages[: opts["limit"]]

        self.stdout.write(f"Considering {len(pages)} page(s).")

        translated = skipped = errored = 0
        for page in pages:
            cls_name = type(page).__name__
            page_type, field_pairs = TRANSLATABLE[cls_name]

            payload_fields = {}
            for src, dst in field_pairs:
                src_value = getattr(page, src, None)
                dst_value = getattr(page, dst, None)
                if not src_value:
                    continue
                if dst_value and not opts["force"]:
                    continue
                payload_fields[src] = str(src_value)

            if not payload_fields:
                self.stdout.write(self.style.WARNING(f"  ~ {page.slug}: nothing to translate"))
                skipped += 1
                continue

            payload = {
                "source_lang": "en",
                "target_lang": "pt",
                "page_type": page_type,
                "fields": payload_fields,
            }

            if opts["dry_run"]:
                self.stdout.write(f"  [dry] {page.slug}: would translate {list(payload_fields)}")
                continue

            try:
                result = call_openai(api_key, prompt_id, prompt_version, payload)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ! {page.slug}: OpenAI error: {e}"))
                errored += 1
                continue

            # OpenAI returns either {"fields": {...}} (mirroring input) or flat {...}.
            translated_fields = (
                result.get("fields") if isinstance(result.get("fields"), dict) else result
            )
            applied = 0
            for src, dst in field_pairs:
                if src in translated_fields and translated_fields[src]:
                    setattr(page, dst, translated_fields[src])
                    applied += 1

            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(f"  + {page.slug}: {cls_name} translated ({applied} fields)")
            )
            translated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. translated={translated} skipped={skipped} errored={errored}"
            )
        )
