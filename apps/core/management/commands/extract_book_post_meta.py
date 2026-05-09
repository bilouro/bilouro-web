"""extract_book_post_meta — generate title + summary for each BookPostPage from its body.

For each live BookPostPage, calls OpenAI with a system prompt that produces:
  - a real, evocative title (NOT the bible reference — that goes in `ref`)
  - a 1-2 sentence summary (~25-40 words) shown on listings

Detects the post's source language from the parent BookPage:
  - parent slug "jesus-o-lider"   → source: pt
  - parent slug "jesus-the-leader" → source: en
Sets the matching field directly. Does NOT translate (run translate_pages
separately if you want the other language too).

Usage:
    python manage.py extract_book_post_meta            # all posts missing title/summary
    python manage.py extract_book_post_meta --slug=2026-05-09_jo_13_1-17_pt
    python manage.py extract_book_post_meta --force    # overwrite even if filled
    python manage.py extract_book_post_meta --dry-run

Required env:
    OPENAI_API_KEY
    (optional) OPENAI_BOOKPOST_PROMPT_ID — if set, uses your platform Prompt instead
                                            of the inline system prompt below.
"""
import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.shop.models import BookPostPage


SYSTEM_PROMPT = """You craft short, evocative titles and summaries for devotional reflections by Victor H. Bilouro on his book "Jesus, o Líder" / "Jesus, the Leader" — leadership lessons drawn from passages of the Gospels, written for engineering managers, tech leads, and founders.

You receive JSON: {"lang": "pt"|"en", "ref": "<bible reference>", "body": "<markdown body of the post>"}.

Return JSON with exactly two fields:
  "title": a real title (NOT the bible reference). Should capture the *idea* or *tension* of the reflection. 4-9 words. Title-case. Match the lang. No trailing punctuation.
  "summary": a 1-2 sentence excerpt shown on listing pages, ~25-40 words. Make a reader want to click through. Match the lang. No quotes around the summary.

Style:
  - Strong, concrete verbs. No corporate fluff.
  - First-person voice ("I...") only if the body uses first person prominently.
  - For PT: European Portuguese (Portugal). "tu", "ficheiro", "ecrã".
  - Don't repeat the bible reference inside the title or summary.
  - Don't translate — keep the language of the source body.

Output ONLY valid JSON. No markdown fences, no commentary."""


def call_openai(api_key, prompt_id, ref, body, lang):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    payload = {"lang": lang, "ref": ref, "body": body}

    if prompt_id:
        # Platform Prompt route
        version = os.environ.get("OPENAI_BOOKPOST_PROMPT_VERSION", "1")
        resp = client.responses.create(
            prompt={"id": prompt_id, "version": version},
            input=json.dumps(payload, ensure_ascii=False),
        )
        text = (resp.output_text or "").strip()
    else:
        # Inline system-prompt route (no platform Prompt needed)
        resp = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


class Command(BaseCommand):
    help = "Generate title + summary for BookPostPage entries via OpenAI."

    def add_arguments(self, parser):
        parser.add_argument("--slug")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        api_key = os.environ.get("OPENAI_API_KEY")
        prompt_id = os.environ.get("OPENAI_BOOKPOST_PROMPT_ID")
        if not api_key:
            raise CommandError("OPENAI_API_KEY required")

        qs = BookPostPage.objects.live()
        if opts["slug"]:
            qs = qs.filter(slug=opts["slug"])

        for post in qs:
            parent = post.get_parent().specific
            parent_slug = getattr(parent, "slug", "")
            lang = "pt" if parent_slug == "jesus-o-lider" else "en"

            # Decide which fields to fill
            if lang == "pt":
                title_field = "title_pt"
                summary_field = "summary_pt"
            else:
                title_field = "title"  # native
                summary_field = "summary"

            current_title = getattr(post, title_field) or ""
            current_summary = getattr(post, summary_field) or ""

            # Skip if already filled and the title is NOT the ref
            if not opts["force"]:
                if current_summary and current_title and current_title != post.ref:
                    self.stdout.write(self.style.WARNING(f"  ~ {post.slug}: already filled; skipping"))
                    continue

            if not post.body_md:
                self.stdout.write(self.style.WARNING(f"  ~ {post.slug}: no body; skipping"))
                continue

            if opts["dry_run"]:
                self.stdout.write(f"  [dry] {post.slug} (lang={lang}): would extract title+summary")
                continue

            try:
                result = call_openai(api_key, prompt_id, post.ref, post.body_md, lang)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ! {post.slug}: {e}"))
                continue

            title = (result.get("title") or "").strip()
            summary = (result.get("summary") or "").strip()
            if title:
                setattr(post, title_field, title)
            if summary:
                setattr(post, summary_field, summary)
            post.save_revision().publish()

            self.stdout.write(
                self.style.SUCCESS(
                    f"  + {post.slug} ({lang}): {title!r} | summary {len(summary)} chars"
                )
            )
