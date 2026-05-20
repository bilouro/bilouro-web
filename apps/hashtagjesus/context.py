"""Helpers to inject locale-aware context into Wagtail page renders.

- inject_locale_context(ctx, request, page): used by per-locale pages (br/pt/en)
  to populate header/footer links + html_lang based on the current Site hostname.
- build_picker_context(ctx, request): used only by the apex LanguagePickerPage to
  build the 3-card locale grid + CF-IPCountry-detected suggestion.
"""
from __future__ import annotations

from wagtail.models import Site

HOST_TO_LOCALE = {
    "br.hashtag-jesus.com": ("br", "pt-br"),
    "pt.hashtag-jesus.com": ("pt", "pt-pt"),
    "en.hashtag-jesus.com": ("en", "en"),
}

COUNTRY_TO_LOCALE = {
    "BR": "br",
    "PT": "pt",
}

LOCALES = [
    {"code": "br", "name": "Brasil",   "label": "pt-BR",   "flag": "🇧🇷",
     "url": "https://br.hashtag-jesus.com/", "hreflang": "pt-br"},
    {"code": "pt", "name": "Portugal", "label": "pt-PT",   "flag": "🇵🇹",
     "url": "https://pt.hashtag-jesus.com/", "hreflang": "pt-pt"},
    {"code": "en", "name": "English",  "label": "Global",  "flag": "🌐",
     "url": "https://en.hashtag-jesus.com/", "hreflang": "en"},
]

# Labels per locale (header/footer/etc). Light-touch i18n: enough for now.
LABELS = {
    "br": {
        # nav / sections
        "blog_label": "Reflexões",
        "book_label": "O livro",
        "read_more_label": "Ler",
        "recent_label": "Últimas reflexões",
        "no_posts_label": "Em breve.",
        "back_label": "Voltar",
        "privacy_label": "Privacidade",
        "other_languages_label": "Outros idiomas",
        # book teaser
        "launch_label": "Lançamento previsto",
        # newsletter form
        "newsletter_form_label": "Quero saber quando lançar",
        "newsletter_button": "Inscrever",
        "newsletter_placeholder": "voce@email.com",
        "newsletter_fineprint": "Você vai receber um email para confirmar. Nunca spam.",
        # newsletter thanks
        "thanks_already_title": "Você já está na lista.",
        "thanks_already_body": "Obrigado pelo entusiasmo. Avisamos quando o livro estiver pronto.",
        "thanks_title": "Obrigado.",
        "thanks_body": "Você vai receber um email para confirmar o seu endereço. Sem confirmação, não enviamos nada.",
        # picker
        "picker_suggested_pill": "Sugerido",
        "picker_fineprint": "Detectado pelo seu país. Você pode mudar a qualquer momento.",
        "picker_headline_default": "Escolha o seu idioma",
        "meta_description_default": "Um livro e reflexões semanais sobre Jesus para 2026.",
    },
    "pt": {
        # nav / sections
        "blog_label": "Reflexões",
        "book_label": "O livro",
        "read_more_label": "Ler",
        "recent_label": "Últimas reflexões",
        "no_posts_label": "Em breve.",
        "back_label": "Voltar",
        "privacy_label": "Privacidade",
        "other_languages_label": "Outras línguas",
        # book teaser
        "launch_label": "Lançamento previsto",
        # newsletter form
        "newsletter_form_label": "Quero saber quando lançar",
        "newsletter_button": "Inscrever",
        "newsletter_placeholder": "tu@email.com",
        "newsletter_fineprint": "Vais receber um email para confirmares. Nunca spam.",
        # newsletter thanks
        "thanks_already_title": "Já estás na lista.",
        "thanks_already_body": "Obrigado pelo entusiasmo. Avisamos-te quando o livro estiver pronto.",
        "thanks_title": "Obrigado.",
        "thanks_body": "Vais receber um email para confirmares o teu endereço. Sem confirmação, não te enviamos nada.",
        # picker
        "picker_suggested_pill": "Sugerido",
        "picker_fineprint": "Detectado pelo teu país. Podes mudar a qualquer momento.",
        "picker_headline_default": "Escolhe a tua língua",
        "meta_description_default": "Um livro e reflexões semanais sobre Jesus para 2026.",
    },
    "en": {
        # nav / sections
        "blog_label": "Reflections",
        "book_label": "The book",
        "read_more_label": "Read",
        "recent_label": "Latest reflections",
        "no_posts_label": "Coming soon.",
        "back_label": "Back",
        "privacy_label": "Privacy",
        "other_languages_label": "Other languages",
        # book teaser
        "launch_label": "Expected launch",
        # newsletter form
        "newsletter_form_label": "Notify me when it launches",
        "newsletter_button": "Subscribe",
        "newsletter_placeholder": "you@email.com",
        "newsletter_fineprint": "You'll get an email to confirm. Never spam.",
        # newsletter thanks
        "thanks_already_title": "You're already on the list.",
        "thanks_already_body": "Thanks for the enthusiasm. We'll tell you when the book is ready.",
        "thanks_title": "Thank you.",
        "thanks_body": "You'll get an email to confirm your address. Without confirmation we don't send anything.",
        # picker
        "picker_suggested_pill": "Suggested",
        "picker_fineprint": "Detected from your country. You can switch any time.",
        "picker_headline_default": "Choose your language",
        "meta_description_default": "A book and weekly reflections on Jesus for 2026.",
    },
}


def _host(request) -> str:
    return request.get_host().split(":")[0].lower()


def _site_root_url(request) -> str | None:
    site = Site.find_for_request(request)
    if not site:
        return None
    return site.root_page.url


def inject_locale_context(ctx: dict, request, page) -> None:
    host = _host(request)
    locale_pair = HOST_TO_LOCALE.get(host)
    if locale_pair:
        locale, html_lang = locale_pair
    else:
        locale, html_lang = "en", "en"

    ctx["locale"] = locale
    ctx["html_lang"] = html_lang
    ctx.update(LABELS.get(locale, LABELS["en"]))

    # Try to discover sibling pages (BlogIndex / BookTeaser / Legal) under the
    # current HomePage. Cheap because each Site is tiny.
    site = Site.find_for_request(request)
    if site:
        from .models import HjBlogIndexPage, HjBookTeaserPage, HjLegalPage
        root = site.root_page
        try:
            blog_index = HjBlogIndexPage.objects.live().descendant_of(root).first()
            ctx["blog_index_url"] = blog_index.url if blog_index else None
            book_teaser = HjBookTeaserPage.objects.live().descendant_of(root).first()
            ctx["book_url"] = book_teaser.url if book_teaser else None
            legal = HjLegalPage.objects.live().descendant_of(root).first()
            ctx["legal_url"] = legal.url if legal else None
        except Exception:
            ctx.setdefault("blog_index_url", None)
            ctx.setdefault("book_url", None)
            ctx.setdefault("legal_url", None)


def build_picker_context(ctx: dict, request) -> None:
    cc = (request.headers.get("CF-IPCountry") or "").upper()
    detected = COUNTRY_TO_LOCALE.get(cc, "en")
    ctx["locale"] = detected   # body class for apex (rendered in detected lang)
    ctx["html_lang"] = {"br": "pt-br", "pt": "pt-pt", "en": "en"}.get(detected, "en")
    ctx["locales"] = LOCALES
    ctx["detected"] = detected
    # Strings on the picker render in the detected locale (e.g. BR visitor
    # sees "Sugerido"; EN visitor sees "Suggested").
    ctx.update(LABELS.get(detected, LABELS["en"]))
