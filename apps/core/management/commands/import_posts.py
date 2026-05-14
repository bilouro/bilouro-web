"""Generic post importer — handles two formats:

1. **LinkedIn-style** (used by `linkedin/knowledge-base/posts/`):
       # Post NN — Title
       ## Título sugerido (3 variações)
       1. **first option** *(used)*
       ## Texto (copy-paste)
       ```
       body
       ```

2. **Frontmatter-style** (used by `book_jesus_lider/posts/*` and `book_jesus_leader/posts/*`):
       ---
       ref: João 13:1-17
       lang: pt
       date: 2026-05-09
       image: 2026-05-09_jo_13_1-17_pt.png
       ---
       ![](2026-05-09_jo_13_1-17_pt.png)
       body
       #hashtags

Auto-detects format. Auto-finds image by:
  - frontmatter `image:` field, or
  - same basename as .md (file.md → file.png), or
  - pattern fallback for linkedin numbered posts (post-NN.png ↔ NN-*.md).

Target parent page must be either `tech.BlogIndexPage` or `shop.BookPage`.

Usage:
    python manage.py import_posts /path/to/dir --parent-slug tech [--dry-run] [--limit N]
    python manage.py import_posts /path/to/dir --parent-slug jesus-o-lider
"""
import re
from datetime import date, datetime
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from wagtail.images.models import Image as WagtailImage
from wagtail.models import Page


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse `--- ... ---` YAML-ish frontmatter (key: value, no quoting). Returns (meta, body)."""
    if not text.lstrip().startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta_raw, body = parts[1], parts[2]
    meta = {}
    for line in meta_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip().strip('"').strip("'")
            meta[k.strip()] = v
    return meta, body.lstrip("\n")


def parse_linkedin_format(text: str) -> dict | None:
    """Parse LinkedIn structured posts. Returns None if not matching."""
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
        title = re.sub(r"\*+", "", title)
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    date_match = re.search(r"Published\s*\(?(\d{4}-\d{2}-\d{2})", text)
    post_date = date.today()
    if date_match:
        try:
            post_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return {"title": title, "body": body_match.group(1).strip(), "date": post_date}


def parse_frontmatter_post(text: str, fallback_title: str) -> dict | None:
    """Parse posts with YAML-ish frontmatter (book_jesus_*/posts format)."""
    meta, body = parse_frontmatter(text)
    if not meta:
        return None
    # Strip leading ![](image.png) line
    body_lines = body.lstrip().split("\n")
    if body_lines and body_lines[0].strip().startswith("!["):
        body_lines = body_lines[1:]
    body = "\n".join(body_lines).lstrip()
    # Strip trailing hashtag-only line
    body_lines = body.rstrip().split("\n")
    if body_lines and body_lines[-1].strip().startswith("#") and " " not in body_lines[-1].lstrip("#").strip()[:50]:
        body_lines = body_lines[:-1]
    body = "\n".join(body_lines).rstrip()
    title = meta.get("ref", fallback_title)
    post_date = date.today()
    if meta.get("date"):
        try:
            post_date = datetime.strptime(meta["date"], "%Y-%m-%d").date()
        except ValueError:
            pass
    return {
        "title": title,
        "body": body,
        "date": post_date,
        "ref": meta.get("ref", ""),
        "image_filename": meta.get("image"),
    }


def parse_plain_markdown(text: str, fallback_title: str) -> dict:
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = h1.group(1).strip() if h1 else fallback_title
    return {"title": title, "body": text, "date": date.today()}


def find_image(md_path: Path, image_filename_hint: str | None) -> Path | None:
    """Find a matching image file next to the .md."""
    parent = md_path.parent
    # 1. Hint from frontmatter
    if image_filename_hint:
        cand = parent / image_filename_hint
        if cand.exists():
            return cand
    # 2. Same basename
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        cand = md_path.with_suffix(ext)
        if cand.exists():
            return cand
    # 3. Pattern fallback for LinkedIn numbered posts:
    #    file: 02-voice-agent-overview.md → look for post-2.png, post-02.png, post02.png
    m = re.match(r"^(\d{2})", md_path.stem)
    if m:
        n = int(m.group(1))
        for pattern in (f"post-{n:02d}.png", f"post{n:02d}.png", f"post-{n}.png", f"post{n}.png"):
            cand = parent / pattern
            if cand.exists():
                return cand
    return None


def get_or_create_wagtail_image(image_path: Path, title: str, description: str = "") -> WagtailImage:
    """Upload an image to Wagtail (or return existing by title).

    `description` is used by Wagtail's accessibility checker as the default
    alt text. Pass a meaningful sentence (e.g. the page title) — leaving it
    empty causes the checker to flag the alt as "inappropriate pattern"
    because it falls back to the slug-style image title.
    """
    existing = WagtailImage.objects.filter(title=title).first()
    if existing:
        if description and not existing.description:
            existing.description = description[:255]
            existing.save(update_fields=["description"])
        return existing
    with open(image_path, "rb") as f:
        return WagtailImage.objects.create(
            title=title,
            description=description[:255],
            file=File(f, name=image_path.name),
        )


class Command(BaseCommand):
    help = "Import posts (LinkedIn or frontmatter format) into a BlogIndexPage or BookPage."

    def add_arguments(self, parser):
        parser.add_argument("source_dir")
        parser.add_argument("--parent-slug", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts):
        source = Path(opts["source_dir"])
        if not source.is_dir():
            raise CommandError(f"Not a directory: {source}")

        parent = Page.objects.filter(slug=opts["parent_slug"]).first()
        if not parent:
            raise CommandError(f"No page with slug '{opts['parent_slug']}'")
        parent = parent.specific

        # Lazy imports to avoid circulars on app startup
        from apps.shop.models import BookPage, BookPostPage
        from apps.tech.models import BlogIndexPage, BlogPostPage

        if isinstance(parent, BlogIndexPage):
            target_class = BlogPostPage
        elif isinstance(parent, BookPage):
            target_class = BookPostPage
        else:
            raise CommandError(
                f"Parent must be BlogIndexPage or BookPage, got {type(parent).__name__}"
            )

        md_files = sorted(source.glob("*.md"))
        if opts["limit"]:
            md_files = md_files[: opts["limit"]]

        created = skipped = 0
        for path in md_files:
            if path.stem.lower() in {"readme", "index", "_index"}:
                continue
            text = path.read_text(encoding="utf-8")
            slug = slugify(path.stem)

            parsed = (
                parse_frontmatter_post(text, path.stem)
                or parse_linkedin_format(text)
                or parse_plain_markdown(text, path.stem)
            )
            if not parsed.get("title"):
                self.stdout.write(self.style.WARNING(f"  ! {path.name}: no title; skipping"))
                skipped += 1
                continue

            image_path = find_image(path, parsed.get("image_filename"))

            if opts["dry_run"]:
                img_note = f"img:{image_path.name}" if image_path else "no img"
                self.stdout.write(
                    f"  [dry] {slug}: {parsed['title'][:60]} ({len(parsed['body'])} chars, {img_note})"
                )
                continue

            if target_class.objects.filter(slug=slug).exists():
                self.stdout.write(self.style.WARNING(f"  ~ {slug}: exists, skipping"))
                skipped += 1
                continue

            wagtail_image = None
            if image_path:
                wagtail_image = get_or_create_wagtail_image(
                    image_path, slug, description=parsed["title"][:255]
                )

            kwargs = dict(
                title=parsed["title"][:255],
                slug=slug,
                date=parsed["date"],
                body_md=parsed["body"],
                image=wagtail_image,
            )
            if target_class is BlogPostPage:
                kwargs["intro"] = parsed["body"][:300].split("\n", 1)[0]
            elif target_class is BookPostPage:
                kwargs["ref"] = parsed.get("ref", "")

            page = target_class(**kwargs)
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(f"  + {slug}: {parsed['title'][:60]} {'[+img]' if wagtail_image else ''}")
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. created={created} skipped={skipped} total={len(md_files)}")
        )
