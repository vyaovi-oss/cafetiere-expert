# Cafetière Expert – mode d'emploi

## Écrire un article
1. Va sur https://app.pagescms.org et connecte-toi avec GitHub
2. Ouvre le dépôt cafetiere-expert → Articles → Add an entry
3. Remplis les champs (titre, adresse, description, catégorie, produits…)
4. Clique sur Save : le site se met à jour tout seul en 1 à 2 minutes

## Liens Amazon
- Dans « Lien Amazon » : colle le lien du produit OU son code ASIN.
- Ton identifiant partenaire se règle une seule fois dans « Réglages du site ».
  Il est ajouté automatiquement à TOUS les liens Amazon du site.

## Dossiers
- contenu/articles : les articles (fichiers .md)
- contenu/pages : À propos, Contact, Mentions légales, Confidentialité
- contenu/categories.json / contenu/site.json : catégories et réglages
- templates : le design des pages (ne pas toucher sans Claude)
- static : CSS, favicon, images (static/media)
- build.py : le programme qui fabrique le site (dossier _site)

## Réglages Cloudflare Pages
- Build command : pip install -r requirements.txt && python3 build.py
- Build output directory : _site
