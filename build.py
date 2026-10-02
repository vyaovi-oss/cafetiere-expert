"""
Cafetière Expert — générateur du site.

Lit le contenu (dossier `contenu/`, modifié depuis le panel Pages CMS),
l'assemble avec les modèles (dossier `templates/`) et produit le site
final dans le dossier `_site/`, que Cloudflare Pages met en ligne.

Lancer en local :  python3 build.py
"""
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote_plus, urlsplit, urlunsplit, parse_qsl, urlencode

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

RACINE = Path(__file__).parent
CONTENU = RACINE / "contenu"
SORTIE = RACINE / "_site"

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

erreurs = []


# ---------------------------------------------------------------- utilitaires
def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def lire_markdown(chemin):
    """Sépare l'en-tête YAML (entre ---) du texte de l'article."""
    texte = chemin.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", texte, re.S)
    if not m:
        return {}, texte
    donnees = yaml.safe_load(m.group(1)) or {}
    return donnees, m.group(2)


def en_date(v):
    if not v:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def date_fr(d):
    if not d:
        return ""
    jour = "1er" if d.day == 1 else str(d.day)
    return f"{jour} {MOIS[d.month - 1]} {d.year}"


def en_texte(x):
    """Un point écrit « Texte : suite » sans guillemets devient un dictionnaire en YAML : on le remet en texte."""
    if isinstance(x, dict):
        return " ; ".join(f"{k} : {v}" if v is not None else str(k) for k, v in x.items())
    return str(x)


def slugifier(texte):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t


def rendre_md(texte):
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": lambda v, s: slugifier(v)}})
    html = md.convert(texte or "")
    sommaire = [(t["id"], t["name"]) for t in md.toc_tokens if t["level"] == 2]
    # Les titres h2 sont souvent imbriqués sous un h1 : on les récupère aussi
    for t in md.toc_tokens:
        if t["level"] == 1:
            sommaire += [(c["id"], c["name"]) for c in t["children"] if c["level"] == 2]
    return html, sommaire


# ------------------------------------------------------------ liens Amazon
def lien_amazon(valeur, tag):
    """Accepte un ASIN (ex. B000CQ3AIW), une URL Amazon ou un lien amzn.to."""
    v = (valeur or "").strip()
    if not v:
        return ""
    if re.fullmatch(r"[A-Z0-9]{10}", v):
        v = f"https://www.amazon.fr/dp/{v}"
    elif not v.startswith("http"):
        v = f"https://www.amazon.fr/s?k={quote_plus(v)}"
    return ajouter_tag(v, tag)


def ajouter_tag(url, tag):
    hote = urlsplit(url).netloc.lower()
    if "amazon." not in hote or not tag:
        return url  # amzn.to / amzn.eu contiennent déjà ton identifiant
    parts = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "tag"]
    params.append(("tag", tag))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


def affilier_html(html, tag):
    """Ajoute l'identifiant Amazon et les attributs obligatoires à tous les liens Amazon."""
    def remplace(m):
        attrs = m.group(1)
        href = re.search(r'href="([^"]+)"', attrs)
        if not href:
            return m.group(0)
        url = href.group(1).replace("&amp;", "&")
        hote = urlsplit(url).netloc.lower()
        if not ("amazon." in hote or "amzn." in hote):
            return m.group(0)
        nouvelle = ajouter_tag(url, tag).replace("&", "&amp;")
        attrs = attrs.replace(href.group(0), f'href="{nouvelle}"')
        attrs = re.sub(r'\s(rel|target)="[^"]*"', "", attrs)
        return f'<a{attrs} target="_blank" rel="sponsored nofollow noopener">'
    return re.sub(r"<a(\s[^>]*)>", remplace, html)


# ---------------------------------------------------------------- chargement
site = lire_json(CONTENU / "site.json")
site["url"] = site.get("url", "").rstrip("/")
tag = (site.get("tag_amazon") or "").strip()
categories = lire_json(CONTENU / "categories.json")["categories"]
cat_par_slug = {c["slug"]: c for c in categories}

articles = []
slugs_vus = {c["slug"] for c in categories} | {"guides", "media", "assets"}
for f in sorted((CONTENU / "articles").glob("*.md")):
    try:
        d, corps = lire_markdown(f)
    except yaml.YAMLError as e:
        erreurs.append(f"{f.name} : en-tête mal formé ({e.problem}, ligne {e.problem_mark.line + 1 if e.problem_mark else '?'})")
        continue
    if d.get("brouillon"):
        continue
    slug = slugifier(d.get("slug") or f.stem)
    if not d.get("titre"):
        erreurs.append(f"{f.name} : le titre est vide")
        continue
    if slug in slugs_vus:
        erreurs.append(f"{f.name} : l'adresse « {slug} » est déjà utilisée")
        continue
    slugs_vus.add(slug)
    d["slug"] = slug
    d["url"] = f"/{slug}/"
    d["date"] = en_date(d.get("date")) or dt.date.today()
    d["maj"] = en_date(d.get("maj")) or d["date"]
    d["date_txt"] = date_fr(d["date"])
    d["maj_txt"] = date_fr(d["maj"])
    d["cat"] = cat_par_slug.get(d.get("categorie"))
    cover = d.get("image") or d.get("image_url") or ""
    d["cover"] = cover
    d["cover_abs"] = cover if cover.startswith("http") else (site["url"] + cover if cover else "")
    d["corps"], d["sommaire"] = rendre_md(corps)
    d["intro_html"] = rendre_md(d.get("intro") or "")[0]
    for p in d.get("produits") or []:
        p["lien_final"] = lien_amazon(p.get("lien") or p.get("nom"), tag)
        p["points_forts"] = [en_texte(x) for x in (p.get("points_forts") or []) if x]
        p["points_faibles"] = [en_texte(x) for x in (p.get("points_faibles") or []) if x]
    d["produits"] = d.get("produits") or []
    d["faq"] = [q for q in (d.get("faq") or []) if q.get("question")]
    for q in d["faq"]:
        q["reponse_html"] = rendre_md(q.get("reponse") or "")[0]
    mots = len(re.sub(r"<[^>]+>", " ", d["corps"] + d["intro_html"]).split()) \
        + sum(len(str(p.get("resume", "")).split()) for p in d["produits"])
    d["lecture"] = max(2, round(mots / 200))
    articles.append(d)

articles.sort(key=lambda a: a["date"], reverse=True)

pages = []
for f in sorted((CONTENU / "pages").glob("*.md")):
    d, corps = lire_markdown(f)
    d["slug"] = f.stem
    d["url"] = f"/{f.stem}/"
    d["corps"] = rendre_md(corps)[0]
    pages.append(d)

if erreurs:
    print("❌ Le site n'a pas été construit :")
    for e in erreurs:
        print("   -", e)
    sys.exit(1)

# ---------------------------------------------------------------- génération
if SORTIE.exists():
    shutil.rmtree(SORTIE)
shutil.copytree(RACINE / "static", SORTIE)

env = Environment(loader=FileSystemLoader(RACINE / "templates"),
                  autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
env.globals.update(site=site, categories=categories, annee=dt.date.today().year, version=dt.datetime.now().strftime("%Y%m%d%H%M"))


def ecrire(url, template, **ctx):
    html = env.get_template(template).render(url_page=url, **ctx)
    html = affilier_html(html, tag)
    if url.endswith("/"):
        chemin = SORTIE / url.strip("/") / "index.html"
    else:
        chemin = SORTIE / url.lstrip("/")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(html, encoding="utf-8")


ecrire("/", "accueil.html", articles=articles)
ecrire("/guides/", "guides.html", articles=articles)
for c in categories:
    lies = [a for a in articles if a.get("categorie") == c["slug"]]
    titres = {a["titre"].strip().lower() for a in lies}
    prevus = [t for t in (c.get("prevus") or []) if t and t.strip().lower() not in titres]
    ecrire(f"/{c['slug']}/", "categorie.html", cat=c, articles=lies, prevus=prevus)
for a in articles:
    similaires = [x for x in articles if x is not a and x.get("categorie") == a.get("categorie")][:3]
    if len(similaires) < 3:
        similaires += [x for x in articles if x is not a and x not in similaires][:3 - len(similaires)]
    ecrire(a["url"], "article.html", a=a, similaires=similaires)
for p in pages:
    ecrire(p["url"], "page.html", p=p)
ecrire("/404.html", "404.html")

# sitemap + robots
aujourd = dt.date.today().isoformat()
lignes = [(f"{site['url']}/", aujourd), (f"{site['url']}/guides/", aujourd)]
lignes += [(f"{site['url']}/{c['slug']}/", aujourd) for c in categories]
lignes += [(site["url"] + a["url"], a["maj"].isoformat()) for a in articles]
lignes += [(site["url"] + p["url"], aujourd) for p in pages]
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sm += [f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>" for u, d in lignes]
sm.append("</urlset>")
(SORTIE / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
(SORTIE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site['url']}/sitemap.xml\n", encoding="utf-8")

print(f"✅ Site construit : {len(articles)} article(s), {len(categories)} catégories, {len(pages)} pages.")
