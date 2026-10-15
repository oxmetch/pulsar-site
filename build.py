#!/usr/bin/env python3
"""Build the static site into dist/.

src/*.html are templates:
  {{key}}       — text from i18n/<lang>.json
  {{@name}}     — values computed here (lang, URLs, switcher…)
  [[name]]      — raw snippet from src/partials/<name>.svg

Output: EN at /, RU at /ru/, KZ at /kz/ (same layout, different text).
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
SRC, DIST = ROOT / "src", ROOT / "dist"
SITE = "https://pulsar-ai.co"
# URL of the Cloudflare Worker that forwards form submissions to Telegram (tools/telegram-worker.js).
# Empty = the contact form falls back to opening an email draft.
FORM_ENDPOINT = "https://pulsar-leads.abdinagii03.workers.dev"

LANGS = [
    # code (json + hreflang), html lang, url prefix, switcher label, og locale
    {"code": "en", "html": "en", "prefix": "/", "label": "EN", "og": "en_US"},
    {"code": "kk", "html": "kk", "prefix": "/kz/", "label": "KZ", "og": "kk_KZ"},
    {"code": "ru", "html": "ru", "prefix": "/ru/", "label": "RU", "og": "ru_RU"},
]
PAGES = {"index.html": "", "privacy.html": "privacy/"}  # template -> path under prefix


# old URL (file in dist) -> new URL; GitHub Pages has no server redirects
REDIRECTS = {
    "privacy.html": "/privacy/",
    "kk/index.html": "/kz/",
    "kk/privacy/index.html": "/kz/privacy/",
}


def redirect_page(url):
    return (f'<!doctype html><meta charset="utf-8"><title>Redirecting…</title>'
            f'<link rel="canonical" href="{SITE}{url}"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={url}"><a href="{url}">{SITE}{url}</a>\n')


def load_strings():
    data = {l["code"]: json.loads((ROOT / "i18n" / f"{l['code']}.json").read_text()) for l in LANGS}
    base = set(data["en"])
    for code, d in data.items():
        missing, extra = base - set(d), set(d) - base
        if missing or extra:
            sys.exit(f"i18n/{code}.json: missing {sorted(missing)} extra {sorted(extra)}")
    return data


def lang_switch(page_path, current, strings):
    links = []
    for l in LANGS:
        attrs = ' aria-current="page"' if l is current else ""
        links.append(f'<a href="{l["prefix"]}{page_path}" hreflang="{l["html"]}" lang="{l["html"]}"{attrs}>{l["label"]}</a>')
    return f'        <nav class="lang" aria-label="{strings["lang.label"]}">' + "".join(links) + "</nav>"


def alternates(page_path):
    tags = [f'  <link rel="alternate" hreflang="{l["html"]}" href="{SITE}{l["prefix"]}{page_path}">' for l in LANGS]
    tags.append(f'  <link rel="alternate" hreflang="x-default" href="{SITE}/{page_path}">')
    return "\n".join(tags)


def render(template, lang, page_path, strings, version):
    values = {
        "lang": lang["html"],
        "lang_label": lang["label"],
        "home": lang["prefix"],
        "privacy": f'{lang["prefix"]}privacy/',
        "canonical": f'{SITE}{lang["prefix"]}{page_path}',
        "alternates": alternates(page_path),
        "lang_switch": lang_switch(page_path, lang, strings),
        "og_locale": lang["og"],
        "version": version,
        "form_endpoint": FORM_ENDPOINT,
    }

    def sub_partial(m):
        return (SRC / "partials" / f"{m.group(1)}.svg").read_text().strip()

    def sub_key(m):
        key = m.group(1)
        if key.startswith("@"):
            return values[key[1:]]
        if key not in strings:
            sys.exit(f"Unknown i18n key: {key}")
        return strings[key]

    out = re.sub(r"\[\[([\w-]+)\]\]", sub_partial, template)
    out = re.sub(r"\{\{\s*(@?[\w.]+)\s*\}\}", sub_key, out)
    return out


def main():
    data = load_strings()
    version = time.strftime("%Y%m%d%H%M")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "assets", DIST / "assets", ignore=shutil.ignore_patterns(".DS_Store"))
    for f in ["robots.txt", "sitemap.xml", "site.webmanifest"]:
        shutil.copy(ROOT / f, DIST / f)
    # GitHub Pages: custom domain, no Jekyll, and static stand-ins for the old Netlify redirects
    (DIST / "CNAME").write_text("pulsar-ai.co\n")
    (DIST / ".nojekyll").write_text("")
    shutil.copy(ROOT / "assets/img/favicon-48.png", DIST / "favicon.ico")
    for old, new in REDIRECTS.items():
        target = DIST / old
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(redirect_page(new))

    for tpl_name, page_path in PAGES.items():
        template = (SRC / tpl_name).read_text()
        for lang in LANGS:
            target = DIST / lang["prefix"].strip("/") / page_path / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render(template, lang, page_path, data[lang["code"]], version))
            print("built", target.relative_to(ROOT))


if __name__ == "__main__":
    main()
