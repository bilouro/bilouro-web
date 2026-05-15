"""Import markdown files as BlogPostPage entries.

Usage:
    python manage.py import_markdown /path/to/dir --parent-slug tech-blog [--dry-run]

Handles the LinkedIn-style sectioned format:
    # Post NN — Title

    **Status:** ✅ Published (YYYY-MM-DD)

    ## Título sugerido (3 variações)
    1. **First option** *(used)*

    ## Texto (copy-paste)
    ```
    actual post body
    ```

The importer extracts the chosen title (first item, stripped of markers) and
the body inside the triple-backtick block. Falls back gracefully if the file
is plain markdown (whole content becomes the body, filename → slug+title).
"""
import re
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from wagtail.models import Page

from apps.tech.models import BlogIndexPage, BlogPostPage


def parse_linkedin_format(text: str) -> dict | None:
    """Try to parse the LinkedIn-style structured posts. Returns None if not matching."""
    title_match = re.search(
        r"##\s*Título sugerido[^\n]*\n+\s*1\.\s*(.+?)(?=\n\s*2\.|\n##|$)",
        text,
        re.DOTALL,
    )
    body_match = re.search(
        r"##\s*Texto.*?\n+```[a-z]*\n(.*?)\n```",
        text,
        re.DOTALL,
    )
    if not body_match:
        return None

    title = ""
    if title_match:
        title = title_match.group(1).strip()
        # Strip markdown bold and parenthetical "(used)" / "(usado)"
        title = re.sub(r"\*+", "", title)
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
        title = title.strip()

    date_match = re.search(r"Published\s*\(?(\d{4}-\d{2}-\d{2})", text)
    post_date = date.today()
    if date_match:
        try:
            post_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    return {
        "title": title,
        "body": body_match.group(1).strip(),
        "date": post_date,
    }


def parse_plain_markdown(text: str, fallback_title: str) -> dict:
    """Fallback: use first H1 as title (or filename), rest as body."""
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = h1.group(1).strip() if h1 else fallback_title
    body = text
    return {"title": title, "body": body, "date": date.today()}


class Command(BaseCommand):
    help = "Import markdown files as BlogPostPage entries under a BlogIndexPage."

    def add_arguments(self, parser):
        parser.add_argument("source_dir", help="Directory containing .md files")
        parser.add_argument(
            "--parent-slug",
            default="tech",
            help="Slug of the BlogIndexPage parent (default: tech)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Parse without creating pages"
        )
        parser.add_argument(
            "--limit", type=int, default=None, help="Limit number of files imported"
        )

    def handle(self, *args, **opts):
        source = Path(opts["source_dir"])
        if not source.is_dir():
            raise CommandError(f"Not a directory: {source}")

        parent = BlogIndexPage.objects.filter(slug=opts["parent_slug"]).first()
        if not parent and not opts["dry_run"]:
            raise CommandError(
                f"BlogIndexPage with slug '{opts['parent_slug']}' not found. "
                "Create it in the Wagtail admin first."
            )

        md_files = sorted(source.glob("*.md"))
        if opts["limit"]:
            md_files = md_files[: opts["limit"]]

        created = 0
        skipped = 0
        for path in md_files:
            if path.stem.lower() in {"readme", "index", "_index"}:
                continue
            text = path.read_text(encoding="utf-8")
            slug = slugify(path.stem)

            parsed = parse_linkedin_format(text) or parse_plain_markdown(text, path.stem)

            if not parsed.get("title"):
                self.stdout.write(self.style.WARNING(f"  ! {path.name}: no title; skipping"))
                skipped += 1
                continue

            if opts["dry_run"]:
                self.stdout.write(
                    f"  [dry] {slug}: {parsed['title'][:60]} ({len(parsed['body'])} chars)"
                )
                continue

            if BlogPostPage.objects.filter(slug=slug).exists():
                self.stdout.write(self.style.WARNING(f"  ~ {slug}: exists, skipping"))
                skipped += 1
                continue

            page = BlogPostPage(
                title=parsed["title"][:255],
                slug=slug,
                date=parsed["date"],
                intro=parsed["body"][:300].split("\n", 1)[0],
                body_md=parsed["body"],
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"  + {slug}: {parsed['title'][:60]}"))
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. created={created} skipped={skipped} total={len(md_files)}")
        )
