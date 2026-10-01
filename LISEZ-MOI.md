# Cafetière Expert – mode d'emploi

## 1. Ton identifiant Amazon
Quand tu auras ton compte Partenaires Amazon, remplace partout `VOTRETAG-21`
par ton vrai identifiant (ex. `cafetiereexp-21`).
Dans VS Code : Cmd + Maj + H → rechercher `VOTRETAG-21` → remplacer tout.

## 2. Ajouter un article
1. Copie le dossier `modeles/article-comparatif`
2. Colle-le dans le dossier de la catégorie voulue ou dans `guides/`,
   et renomme-le avec le mot-clé (ex. `meilleure-cafetiere-italienne`)
3. Remplace tout ce qui est entre [crochets] et les `ASIN_ICI`
4. Supprime l'encadré jaune « MODÈLE » et passe `noindex, nofollow` à `index, follow`
5. Ajoute le lien de l'article dans la page de sa catégorie et dans `sitemap.xml`

(Ou demande simplement à Claude d'écrire l'article complet.)

## 3. Structure
- `index.html` : accueil
- `machines-expresso/`, `machines-a-grain/`, ... : catégories
- `guides/` : guides pratiques
- `assets/style.css` : le design
- `sitemap.xml` / `robots.txt` : pour Google
