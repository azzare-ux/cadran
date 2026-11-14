"""
Poste dans le canal Telegram le lien de la nouvelle édition Cadran.

Variables d'environnement (fournies par le workflow) :
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID  -> secrets du repo
  PAGE_URL  -> adresse du site (ex : https://azzare-ux.github.io/cadran/)
  LATEST    -> nom du fichier de l'édition (ex : recap-horlogerie-semaine-14-20-sept-2026.html)

Le script n'utilise que la bibliothèque standard de Python (rien à installer).
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def clean(text):
    """Enlève les balises, les entités HTML (&amp;, &nbsp;...) et les espaces en trop."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_edition(path):
    """Lit le titre, le titre principal et le résumé d'une édition."""
    with open(path, encoding="utf-8") as f:
        page = f.read()

    def first(pattern):
        match = re.search(pattern, page, re.S | re.I)
        return clean(match.group(1)) if match else ""

    title = first(r"<title>(.*?)</title>")
    headline = first(r"<h1[^>]*>(.*?)</h1>")
    teaser = first(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']*)["\']')

    period = ""
    match = re.search(r"semaine\s+(du\s+.+)$", title, re.I)
    if match:
        period = match.group(1).strip()

    return period, headline, teaser


def build_message(path, page_url, latest):
    period, headline, teaser = read_edition(path)
    url = page_url.rstrip("/") + "/" + urllib.parse.quote(latest)

    lines = [f"📖 Nouvelle édition Cadran" + (f" — semaine {period}" if period else ""), ""]
    if headline:
        lines.append(headline)
    if teaser:
        lines.append(teaser)
    if headline or teaser:
        lines.append("")
    lines.append(f"👉 {url}")
    return "\n".join(lines)


def send(token, chat_id, text):
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "link_preview_options": json.dumps({"is_disabled": True}),
        }
    ).encode("utf-8")
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace").replace(token, "***")
        raise RuntimeError(f"Telegram a refusé l'envoi (HTTP {exc.code}) : {body}") from None
    if not result.get("ok"):
        raise RuntimeError(f"Telegram a refusé l'envoi : {result.get('description')}")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    page_url = os.environ.get("PAGE_URL")
    latest = os.environ.get("LATEST")

    missing = [name for name, value in (
        ("TELEGRAM_TOKEN", token), ("TELEGRAM_CHAT_ID", chat_id),
        ("PAGE_URL", page_url), ("LATEST", latest)) if not value]
    if missing:
        sys.exit("Variable(s) manquante(s) : " + ", ".join(missing))

    message = build_message(latest, page_url, latest)
    print(message)
    send(token, chat_id, message)
    print("Message envoyé dans le canal.")


if __name__ == "__main__":
    main()
