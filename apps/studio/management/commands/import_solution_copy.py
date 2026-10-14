"""Import a solution page's copy + screenshots from a drafts folder.

The folder follows the handoff contract agreed with the content session
(see drafts/studio-app/ when present):

    copy.en.md, copy.pt.md      same skeleton, one per language
    screens/<name>.png          phone screenshots (00-hero.png = page hero)
    screens/captions.md         "filename | EN caption | PT caption" per line

Markdown skeleton (## headings are matched case-insensitively):

    ## Hero                     - eyebrow: / - headline: (*emphasis*) / - sub:
    ## Problem                  one paragraph   (## Problem: Custom heading)
    ## Solution                 one paragraph
    ## Feature N: <title>       - pain: / - steps: (numbered lines) / - screens:
                                - number: value | label / - differentiator:
    ## Also included            - <title> — one line
    ## In numbers               - value | label (x4) / - proof: one line
    ## Closing                  - heading: / - body: / - cta:

Features, extras and stats are REPLACED on import; placeholder steps/benefits
are cleared when features are present (keep them with --keep-steps). Images
are de-duplicated by title (= file name) so re-running is idempotent.

Usage:
    manage.py import_solution_copy                      # drafts/studio-app → /studio-app/
    manage.py import_solution_copy --dir drafts/x --slug x --dry-run
"""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from wagtail.images import get_image_model

from apps.studio.models import (
    StudioSolutionExtra,
    StudioSolutionFaq,
    StudioSolutionFeature,
    StudioSolutionPage,
    StudioSolutionScreen,
    StudioSolutionStat,
)

LANGS = ("en", "pt")
# Fallback emoji per feature position when the copy gives no "- icon:" line.
DEFAULT_ICONS = ["🎟️", "⏳", "📱", "🗓️", "🌱", "✨", "🔔", "📊"]
# Captions may start with "*tall*" (full-page capture) — kept out of the strip.
TALL_RE = re.compile(r"^\*?tall\*?\s*[—–-]?\s*", re.I)
TALL_PT_RE = re.compile(r"^\*?alta\*?\s*[—–-]?\s*", re.I)
FEATURE_RE = re.compile(r"^feature\s*(\d+)\s*:\s*(.+)$", re.I)
KV_RE = re.compile(r"^-\s*\**([a-z_ ]+?)\**\s*:\s*(.*)$", re.I)
NUM_RE = re.compile(r"^(\d+)[.)]\s+(.*)$")


# ─── Parsing ───────────────────────────────────────────────────────────


@dataclass
class Section:
    name: str            # normalised key: hero, problem, solution, feature, extras, numbers, closing
    heading: str         # custom heading after ':' (problem/solution/extras/numbers) or feature title
    index: int           # feature number (1-based) or 0
    kv: dict = field(default_factory=dict)      # "- key: value" pairs (lowercased keys)
    steps: list = field(default_factory=list)   # numbered lines under "- steps:"
    bullets: list = field(default_factory=list) # plain "- ..." bullets (extras, numbers)
    paragraphs: list = field(default_factory=list)
    faqs: list = field(default_factory=list)    # [(question, [answer paragraphs])] in '## FAQ'


SECTION_KEYS = {
    "hero": "hero",
    "problem": "problem",
    "solution": "solution",
    "also included": "extras",
    "in numbers": "numbers",
    "numbers": "numbers",
    "closing": "closing",
    "page": "page",
    "seo": "seo",
    "faq": "faq",
}


def _norm_section(title: str) -> tuple[str, str, int]:
    """'Feature 2: Waitlist' → ('feature', 'Waitlist', 2); 'Problem: X' → ('problem', 'X', 0)."""
    m = FEATURE_RE.match(title.strip())
    if m:
        return "feature", m.group(2).strip(), int(m.group(1))
    base, _, custom = title.partition(":")
    key = SECTION_KEYS.get(base.strip().lower())
    if not key:
        raise CommandError(f"Unknown section '## {title}'")
    return key, custom.strip(), 0


def parse_copy(text: str) -> list[Section]:
    sections: list[Section] = []
    cur: Section | None = None
    in_steps = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            key, heading, idx = _norm_section(line[3:])
            cur = Section(name=key, heading=heading, index=idx)
            sections.append(cur)
            in_steps = False
            continue
        if cur is None or line.startswith("# ") or not line.strip():
            continue
        stripped = line.strip()
        if cur.name == "faq":
            if stripped.startswith("### "):
                cur.faqs.append((stripped[4:].strip(), []))
            elif cur.faqs:
                cur.faqs[-1][1].append(stripped)
            continue
        # numbered step lines (only meaningful after "- steps:")
        nm = NUM_RE.match(stripped)
        if in_steps and nm:
            cur.steps.append(nm.group(2).strip())
            continue
        kv = KV_RE.match(stripped)
        if kv:
            key = kv.group(1).strip().lower().replace(" ", "_")
            val = kv.group(2).strip()
            if key == "steps":
                in_steps = True
                if val:  # steps given inline, "a; b; c"
                    cur.steps.extend(s.strip() for s in val.split(";") if s.strip())
                continue
            in_steps = False
            cur.kv[key] = val
            continue
        if stripped.startswith("- "):
            in_steps = False
            cur.bullets.append(stripped[2:].strip())
            continue
        cur.paragraphs.append(stripped)
    return sections


# ─── Text → (rich)text helpers ─────────────────────────────────────────


def _inline(text: str) -> str:
    """Escape HTML, then allow *em* and **strong** markdown."""
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    # [text](https://url) → link (external URLs only)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t


def _para(lines: list[str]) -> str:
    return "".join(f"<p>{_inline(ln)}</p>" for ln in lines if ln.strip())


def _ol(items: list[str]) -> str:
    return "<ol>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ol>" if items else ""


def _split_pipe(value: str) -> tuple[str, str]:
    """'312 | trial classes' → ('312', 'trial classes'); also accepts ' — '."""
    for sep in ("|", " — ", " - "):
        if sep in value:
            a, b = value.split(sep, 1)
            return a.strip(), b.strip()
    return value.strip(), ""


def _split_dash(value: str) -> tuple[str, str]:
    """'Payroll sheet — one line' → ('Payroll sheet', 'one line')."""
    for sep in (" — ", " – ", " - ", ": "):
        if sep in value:
            a, b = value.split(sep, 1)
            return a.strip(), b.strip()
    return value.strip(), ""


# ─── Command ───────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = "Import copy.en.md / copy.pt.md / screens into a StudioSolutionPage (default: drafts/studio-app → studio-app)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default="drafts/studio-app", help="Drafts folder (default drafts/studio-app)")
        parser.add_argument("--slug", default="studio-app", help="StudioSolutionPage slug (default studio-app)")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report; write nothing")
        parser.add_argument("--keep-steps", action="store_true", help="Do not clear placeholder steps/benefits")
        parser.add_argument("--create", action="store_true", help="Create the page under the studio home if it does not exist (title from '## Page')")

    # -- helpers --------------------------------------------------------

    def _load(self, folder: Path) -> dict[str, dict]:
        """Returns {lang: {section_key: Section | [Section...]}}."""
        out = {}
        for lang in LANGS:
            f = folder / f"copy.{lang}.md"
            if not f.exists():
                raise CommandError(f"Missing {f}")
            secs = parse_copy(f.read_text(encoding="utf-8"))
            by: dict = {"feature": []}
            for s in secs:
                if s.name == "feature":
                    by["feature"].append(s)
                else:
                    by[s.name] = s
            by["feature"].sort(key=lambda s: s.index)
            out[lang] = by
        return out

    def _captions(self, folder: Path) -> dict[str, tuple[str, str, bool]]:
        """{filename: (EN caption, PT caption, is_tall)}."""
        f = folder / "screens" / "captions.md"
        caps: dict[str, tuple[str, str, bool]] = {}
        if not f.exists():
            return caps
        for line in f.read_text(encoding="utf-8").splitlines():
            if "|" not in line or line.lstrip().startswith("#"):
                continue
            parts = [p.strip() for p in line.strip().strip("-").strip().split("|")]
            if len(parts) >= 2 and parts[0]:
                en_cap = parts[1]
                pt_cap = parts[2] if len(parts) > 2 else ""
                tall = bool(TALL_RE.match(en_cap))
                en_cap = TALL_RE.sub("", en_cap).strip()
                pt_cap = TALL_PT_RE.sub("", pt_cap).strip()
                caps[Path(parts[0]).name] = (en_cap, pt_cap, tall)
        return caps

    def _image(self, folder: Path, ref: str, caps: dict):
        """Upload (or reuse) screens/<ref>. Reuse only when an image with the same
        title AND the same file content (sha1) exists → idempotent, but a changed
        screenshot with the same name is uploaded again."""
        ref = ref.strip()
        name = Path(ref).name
        path = (folder / ref).resolve()
        if not path.exists():
            path = folder / "screens" / name
        if not path.exists():
            raise CommandError(f"Screenshot not found: {path}")
        image_model = get_image_model()
        sha1 = hashlib.sha1(path.read_bytes()).hexdigest()  # noqa: S324 — dedup key, not security
        existing = image_model.objects.filter(title=name, file_hash=sha1).first()
        if existing:
            return existing
        with path.open("rb") as fh:
            img = image_model(title=name, file=ImageFile(fh, name=name), file_hash=sha1)
            img.save()
        return img

    # -- main -----------------------------------------------------------

    def handle(self, *args, **opts):
        folder = Path(opts["dir"])
        if not folder.is_dir():
            raise CommandError(f"Not a folder: {folder}")
        data = self._load(folder)
        en, pt = data["en"], data["pt"]
        caps = self._captions(folder)

        # Sanity: both languages must have the same shape.
        for key in ("hero", "problem", "solution"):
            if key not in en or key not in pt:
                raise CommandError(f"Section '{key}' missing in one of the languages")
        if len(en["feature"]) != len(pt["feature"]):
            raise CommandError(f"Feature count differs: en={len(en['feature'])} pt={len(pt['feature'])}")
        n_stats_en = len(en["numbers"].bullets) if en.get("numbers") else 0
        n_stats_pt = len(pt["numbers"].bullets) if pt.get("numbers") else 0
        fq_en = en["faq"].faqs if en.get("faq") else []
        fq_pt = pt["faq"].faqs if pt.get("faq") else []
        if len(fq_en) != len(fq_pt):
            raise CommandError(f"FAQ count differs: en={len(fq_en)} pt={len(fq_pt)}")
        if n_stats_en != n_stats_pt:
            raise CommandError(f"'In numbers' count differs: en={n_stats_en} pt={n_stats_pt}")
        ex_en = en.get("extras").bullets if en.get("extras") else []
        ex_pt = pt.get("extras").bullets if pt.get("extras") else []
        if len(ex_en) != len(ex_pt):
            raise CommandError(f"'Also included' count differs: en={len(ex_en)} pt={len(ex_pt)}")

        page = StudioSolutionPage.objects.filter(slug=opts["slug"]).first()
        pg_en = en["page"].kv if en.get("page") else {}
        pg_pt = pt["page"].kv if pt.get("page") else {}
        if not page and opts["create"] and not opts["dry_run"]:
            from apps.studio.models import StudioHomePage
            home = StudioHomePage.objects.first()
            if not home:
                raise CommandError("No StudioHomePage to create the page under")
            page = StudioSolutionPage(title=pg_en.get("title") or opts["slug"], slug=opts["slug"])
            home.add_child(instance=page)
            self.stdout.write(self.style.SUCCESS(f"  + created /{page.slug}/"))
        if not page and not opts["dry_run"]:
            raise CommandError(f"No StudioSolutionPage with slug '{opts['slug']}' (use --create)")

        self.stdout.write(f"{folder} → /{opts['slug']}/ : {len(en['feature'])} features, {len(ex_en)} extras, {n_stats_en} stats, {len(fq_en)} faqs, {len(caps)} captions")
        for f_en in en["feature"]:
            self.stdout.write(f"  feature {f_en.index}: {f_en.heading} | steps={len(f_en.steps)} screens={f_en.kv.get('screens', '')!r} number={f_en.kv.get('number', '')!r}")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("dry-run: nothing written"))
            return

        # Page-level fields ---------------------------------------------
        def put(field_name, en_val, pt_val):
            setattr(page, field_name, en_val)
            setattr(page, f"{field_name}_pt", pt_val)

        if pg_en.get("title"):
            page.title = pg_en["title"]
        for key in ("nav_label", "verticals_heading", "faq_heading", "features_heading", "extras_heading"):
            if pg_en.get(key):
                put(key, pg_en[key], pg_pt.get(key, ""))
        if pg_en.get("parent"):
            parent = StudioSolutionPage.objects.filter(slug=pg_en["parent"]).first()
            if not parent:
                raise CommandError(f"parent solution '{pg_en['parent']}' not found")
            page.parent_solution = parent
        seo_en = en["seo"].kv if en.get("seo") else {}
        seo_pt = pt["seo"].kv if pt.get("seo") else {}
        if seo_en.get("title"):
            put("seo_title", seo_en["title"], seo_pt.get("title", ""))
        if seo_en.get("description"):
            put("search_description", seo_en["description"], seo_pt.get("description", ""))

        h_en, h_pt = en["hero"].kv, pt["hero"].kv
        put("hero_eyebrow", h_en.get("eyebrow", page.hero_eyebrow), h_pt.get("eyebrow", page.hero_eyebrow_pt))
        if h_en.get("headline"):
            put("hero_headline", _inline(h_en["headline"]), _inline(h_pt.get("headline", "")))
        if h_en.get("sub"):
            put("hero_sub", _para([h_en["sub"]]), _para([h_pt.get("sub", "")]))
        for key, fld in (("problem", "problem"), ("solution", "solution")):
            s_en, s_pt = en[key], pt[key]
            if s_en.heading:
                put(f"{fld}_heading", s_en.heading, s_pt.heading or s_en.heading)
            elif not getattr(page, f"{fld}_heading"):
                default = {"problem": ("The problem", "O problema"), "solution": ("The solution", "A solução")}[fld]
                put(f"{fld}_heading", *default)
            put(f"{fld}_body", _para(s_en.paragraphs), _para(s_pt.paragraphs))
        if en.get("extras") and en["extras"].heading:
            put("extras_heading", en["extras"].heading, pt["extras"].heading or en["extras"].heading)
        elif not page.extras_heading and ex_en:
            put("extras_heading", "Also included", "Também incluído")
        num_en = en.get("numbers")
        num_pt = pt.get("numbers")
        if num_en and num_en.heading:
            put("stats_heading", num_en.heading, num_pt.heading or num_en.heading)
        proof_en = num_en.kv.get("proof") if num_en else ""
        if proof_en:
            put("proof_note", _para([proof_en]), _para([num_pt.kv.get("proof", "")]))
        c_en = en["closing"].kv if en.get("closing") else {}
        c_pt = pt["closing"].kv if pt.get("closing") else {}
        if c_en.get("heading"):
            put("closing_heading", c_en["heading"], c_pt.get("heading", ""))
        if c_en.get("body"):
            put("closing_body", _para([c_en["body"]]), _para([c_pt.get("body", "")]))
        if c_en.get("cta"):
            put("cta_label", c_en["cta"], c_pt.get("cta", ""))

        hero_ref = h_en.get("image") or ("screens/00-hero.png" if (folder / "screens" / "00-hero.png").exists() else "")
        if hero_ref:
            page.image = self._image(folder, hero_ref, caps)

        # Inlines (replace) ---------------------------------------------
        page.features.all().delete()
        used_screens: set[str] = set()
        for pos, (f_en, f_pt) in enumerate(zip(en["feature"], pt["feature"], strict=True)):
            refs = [r.strip() for r in f_en.kv.get("screens", "").split(",") if r.strip()]
            imgs = [self._image(folder, r, caps) for r in refs[:2]]
            used_screens.update(Path(r).name for r in refs[:2])
            val_en, lab_en = _split_pipe(f_en.kv.get("number", ""))
            _, lab_pt = _split_pipe(f_pt.kv.get("number", ""))
            page.features.add(
                StudioSolutionFeature(
                    sort_order=pos,
                    icon=f_en.kv.get("icon") or (DEFAULT_ICONS[pos] if pos < len(DEFAULT_ICONS) else ""),
                    title=f_en.heading, title_pt=f_pt.heading,
                    pain=f_en.kv.get("pain", ""), pain_pt=f_pt.kv.get("pain", ""),
                    body=_ol(f_en.steps), body_pt=_ol(f_pt.steps),
                    image=imgs[0] if imgs else None,
                    image2=imgs[1] if len(imgs) > 1 else None,
                    stat_value=val_en, stat_label=lab_en, stat_label_pt=lab_pt,
                    differentiator=f_en.kv.get("differentiator", ""),
                    differentiator_pt=f_pt.kv.get("differentiator", ""),
                )
            )

        page.extras.all().delete()
        for pos, (x_en, x_pt) in enumerate(zip(ex_en, ex_pt, strict=True)):
            t_en, b_en = _split_dash(x_en)
            t_pt, b_pt = _split_dash(x_pt)
            page.extras.add(StudioSolutionExtra(sort_order=pos, title=t_en, body=b_en, title_pt=t_pt, body_pt=b_pt))

        page.stats.all().delete()
        for pos, (s_en, s_pt) in enumerate(zip(num_en.bullets if num_en else [], num_pt.bullets if num_pt else [], strict=True)):
            v, l_en = _split_pipe(s_en)
            _, l_pt = _split_pipe(s_pt)
            page.stats.add(StudioSolutionStat(sort_order=pos, value=v, label=l_en, label_pt=l_pt))

        # Screens strip: only screenshots NOT already shown inside a feature,
        # and not the full-page ("tall") captures, which don't fit a strip.
        page.screens.all().delete()
        pos = 0
        for name, (cap_en, cap_pt, tall) in caps.items():
            if name in used_screens or name == "00-hero.png" or tall:
                continue
            if (folder / "screens" / name).exists():
                page.screens.add(StudioSolutionScreen(sort_order=pos, image=self._image(folder, name, caps), caption=cap_en, caption_pt=cap_pt))
                pos += 1

        page.faqs.all().delete()
        for pos, ((q_en, a_en), (q_pt, a_pt)) in enumerate(zip(fq_en, fq_pt, strict=True)):
            page.faqs.add(StudioSolutionFaq(sort_order=pos, question=q_en, answer=_para(a_en), question_pt=q_pt, answer_pt=_para(a_pt)))

        if en["feature"] and not opts["keep_steps"]:
            page.steps.all().delete()
            page.benefits.all().delete()

        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(
            f"imported → /{page.slug}/ : features={page.features.count()} extras={page.extras.count()} "
            f"stats={page.stats.count()} faqs={page.faqs.count()} screens={page.screens.count()} hero_image={'yes' if page.image else 'no'}"
        ))
