#!/usr/bin/env python3
"""Build the static site into dist/.

src/*.html are templates:
  {{key}}       — text from i18n/<lang>.json
  {{@name}}     — values computed here (lang, URLs, switcher…)
  [[name]]      — raw snippet from src/partials/<name>.svg

Output: EN at /, RU at /ru/, KZ at /kz/ (same layout, different text).
"""
import html
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

# Search engines and analytics. Paste the IDs here; an empty value means the tag is left out.
GOOGLE_SITE_VERIFICATION = ""  # Search Console → Settings → Ownership verification → HTML tag (content="…")
BING_SITE_VERIFICATION = ""    # Bing Webmaster Tools → <meta name="msvalidate.01" content="…">
YANDEX_SITE_VERIFICATION = ""  # Yandex Webmaster → <meta name="yandex-verification" content="…">
GTM_ID = ""                    # Google Tag Manager container, e.g. "GTM-ABC1234" (GA4 is configured inside GTM)

OG_IMAGE = f"{SITE}/assets/img/og-image.jpg"  # 1200×630, made by tools/make-og-image.swift

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


def plain(text):
    """i18n strings may hold <br> and entities; structured data wants plain text."""
    return html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("  ", " ").strip()


def head_extra():
    tags = []
    if GOOGLE_SITE_VERIFICATION:
        tags.append(f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">')
    if BING_SITE_VERIFICATION:
        tags.append(f'<meta name="msvalidate.01" content="{BING_SITE_VERIFICATION}">')
    if YANDEX_SITE_VERIFICATION:
        tags.append(f'<meta name="yandex-verification" content="{YANDEX_SITE_VERIFICATION}">')
    if GTM_ID:
        tags.append("<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});"
                    "var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
                    "j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);"
                    f"}})(window,document,'script','dataLayer','{GTM_ID}');</script>")
    return "\n".join("  " + t for t in tags)


def body_extra():
    if not GTM_ID:
        return ""
    return (f'  <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_ID}" height="0" width="0" '
            f'style="display:none;visibility:hidden"></iframe></noscript>')


def structured_data(lang, page_url, strings):
    """Schema.org graph for the landing page: organization, site, page, the SmartRail service and its video."""
    org, website, service = f"{SITE}/#organization", f"{SITE}/#website", f"{SITE}/#smartrail"
    graph = [
        {
            "@type": "Organization",
            "@id": org,
            "name": "Pulsar.ai",
            "url": f"{SITE}/",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/img/icon-512.png", "width": 512, "height": 512},
            "image": OG_IMAGE,
            "description": plain(strings["footer.text"]),
            "email": "zhanara.galym@gmail.com",
            "areaServed": {"@type": "Country", "name": "Kazakhstan"},
            "contactPoint": [{
                "@type": "ContactPoint",
                "contactType": "sales",
                "email": "zhanara.galym@gmail.com",
                "availableLanguage": ["English", "Russian", "Kazakh"],
            }],
        },
        {
            "@type": "WebSite",
            "@id": website,
            "url": f"{SITE}/",
            "name": "Pulsar.ai",
            "inLanguage": [l["html"] for l in LANGS],
            "publisher": {"@id": org},
        },
        {
            "@type": "WebPage",
            "@id": f"{page_url}#webpage",
            "url": page_url,
            "name": plain(strings["meta.title"]),
            "description": plain(strings["meta.description"]),
            "inLanguage": lang["html"],
            "isPartOf": {"@id": website},
            "about": {"@id": service},
            "primaryImageOfPage": {"@type": "ImageObject", "url": OG_IMAGE, "width": 1200, "height": 630},
        },
        {
            "@type": "Service",
            "@id": service,
            "name": "SmartRail",
            "serviceType": plain(strings["hero.eyebrow"]),
            "description": plain(strings["sr.p1"]) + " " + plain(strings["sr.p2"]),
            "provider": {"@id": org},
            "areaServed": {"@type": "Country", "name": "Kazakhstan"},
            "audience": [{"@type": "BusinessAudience", "name": plain(strings[k])}
                         for k in ("aud.c1_title", "aud.c2_title", "aud.c3_title", "aud.c4_title")],
        },
        {
            "@type": "VideoObject",
            "name": plain(strings["sr.video_label"]),
            "description": plain(strings["sr.p1"]),
            "thumbnailUrl": f"{SITE}/assets/img/smartrail-poster-v2.jpg",
            "contentUrl": f"{SITE}/assets/video/smartrail-v2.mp4",
            "uploadDate": "2026-10-14",
            "inLanguage": lang["html"],
        },
    ]
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)
    return data.replace("</", "<\\/")  # never close the <script> early


def inline_css():
    """styles.css minified for a <style> tag (comments and extra whitespace removed)."""
    css = (ROOT / "assets/css/styles.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


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
        "og_image": OG_IMAGE,
        "head_extra": head_extra(),
        "body_extra": body_extra(),
        "jsonld": structured_data(lang, f'{SITE}{lang["prefix"]}{page_path}', strings),
        "css": inline_css(),
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
    for f in ["robots.txt", "site.webmanifest"]:
        shutil.copy(ROOT / f, DIST / f)
    # site-root files as-is (search engine verification files etc.)
    for f in (ROOT / "static").iterdir():
        shutil.copy(f, DIST / f.name)
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

    # 404 (GitHub Pages serves dist/404.html with status 404), sitemap and llms.txt
    (DIST / "404.html").write_text(render((SRC / "404.html").read_text(), LANGS[0], "", data["en"], version))
    (DIST / "sitemap.xml").write_text(sitemap(time.strftime("%Y-%m-%d")))
    (DIST / "llms.txt").write_text(llms_txt(data))
    print("built dist/404.html, dist/sitemap.xml, dist/llms.txt")


def sitemap(lastmod):
    """Language versions of the landing page; privacy pages are noindex and stay out."""
    alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{l["html"]}" href="{SITE}{l["prefix"]}"/>' for l in LANGS)
    alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>'
    urls = "".join(f"\n  <url>\n    <loc>{SITE}{l['prefix']}</loc>\n    <lastmod>{lastmod}</lastmod>{alts}\n  </url>"
                   for l in LANGS)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            f"{urls}\n</urlset>\n")


def llms_txt(data):
    """Plain-text brief for AI assistants and answer engines (llmstxt.org format)."""
    en = {k: plain(v) for k, v in data["en"].items()}
    steps = "\n".join(f"{i}. {en[f'how.s{i}_title']}: {en[f'how.s{i}_text']}" for i in range(1, 5))
    audience = "\n".join(f"- {en[f'aud.c{i}_title']}: {en[f'aud.c{i}_text']}" for i in range(1, 5))
    deployments = "\n".join(f"- {en[f'dep.c{i}_kind']}: {en[f'dep.c{i}_text']}" for i in range(1, 4))
    return f"""# Pulsar.ai

> {en['meta.description']}

{en['about.p1']} {en['about.p2']}

## SmartRail
{en['sr.p1']} {en['sr.p2']}

- {en['stats.sec_text']}: 3 seconds
- {en['stats.in1_text']}
- {en['stats.hours_text']}: 2 hours
- {en['stats.history_text']}

## How it works
{steps}

## Digital report
{en['report.lead']}
- {en['report.docs_title']}: {en['report.docs_1']}, {en['report.docs_2']}, {en['report.docs_3']}, {en['report.docs_4']}
- {en['report.scan_title']}: {en['report.scan_sub']}

## Who it's for
{audience}

## Deployments
{deployments}

## Contact
{en['contact.lead']}
Email: zhanara.galym@gmail.com

## Pages
- [English]({SITE}/)
- [Русский]({SITE}/ru/)
- [Қазақша]({SITE}/kz/)
"""


if __name__ == "__main__":
    main()
