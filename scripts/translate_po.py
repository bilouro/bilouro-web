#!/usr/bin/env python3
"""translate_po.py — populate empty msgstr entries in a .po file via OpenAI Prompt.

Usage:
    OPENAI_API_KEY=... OPENAI_TRANSLATION_PROMPT_ID=pmpt_... \\
        python scripts/translate_po.py locale/pt/LC_MESSAGES/django.po pt
"""
import json
import os
import re
import sys

import polib
from openai import OpenAI


def translate_batch(client, prompt_id, version, source_lang, target_lang, strings: dict[str, str]) -> dict[str, str]:
    payload = {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "page_type": "ui_strings",
        "fields": strings,
    }
    resp = client.responses.create(
        prompt={"id": prompt_id, "version": version},
        input=json.dumps(payload, ensure_ascii=False),
    )
    text = (resp.output_text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    return data.get("fields", data) if isinstance(data, dict) else {}


def main():
    po_path = sys.argv[1]
    target_lang = sys.argv[2] if len(sys.argv) > 2 else "pt"

    api_key = os.environ["OPENAI_API_KEY"]
    prompt_id = os.environ["OPENAI_TRANSLATION_PROMPT_ID"]
    version = os.environ.get("OPENAI_TRANSLATION_PROMPT_VERSION", "1")

    po = polib.pofile(po_path)
    untranslated = [e for e in po if not e.msgstr.strip() and not e.obsolete]
    if not untranslated:
        print("Nothing to translate.")
        return

    print(f"Translating {len(untranslated)} entries from .po to {target_lang}...")

    # Build dict {key: source_text}, sanitize keys (no special chars OpenAI might choke on)
    items = {}
    key_to_entry = {}
    for i, e in enumerate(untranslated):
        key = f"k{i:03d}"
        items[key] = e.msgid
        key_to_entry[key] = e

    client = OpenAI(api_key=api_key)
    translated = translate_batch(client, prompt_id, version, "en", target_lang, items)

    applied = 0
    for key, value in translated.items():
        if key in key_to_entry and value:
            key_to_entry[key].msgstr = value
            applied += 1

    # Mark file metadata
    po.metadata["Language"] = target_lang
    po.metadata["Last-Translator"] = "OpenAI Responses API"

    po.save()
    print(f"Wrote {applied} translations to {po_path}")


if __name__ == "__main__":
    main()
