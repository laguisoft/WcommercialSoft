# Importer categorie/produit de `main` vers `Saas`

Sur `main`, `Categorie` et `Produit` sont des tables simples. Sur `Saas`
(multi-tenant), ces mêmes tables ont un champ `entreprise` obligatoire et
leurs contraintes d'unicité (`codebare`, `libelle`, `nom` de catégorie) sont
désormais par entreprise plutôt que globales. On ne peut donc pas faire un
simple `dumpdata` / `loaddata` d'une branche à l'autre : les données de
`main` doivent être rattachées à une entreprise précise au moment de
l'import.

Ce dépôt fournit :
- une commande native Django (`dumpdata`) pour exporter depuis `main` ;
- une commande custom (`import_categorie_produit`, ajoutée dans
  `CommercialSoft/management/commands/`) pour importer dans `Saas`.

## 1. Exporter depuis `main`

Sur la machine/l'environnement où tourne la base de `main` (fichier `.env`
pointant sur cette base) :

```bash
git checkout main
pip install -r requirements.txt   # si besoin
python manage.py dumpdata CommercialSoft.categorie CommercialSoft.produit --indent 2 --output categorie_produit_main.json
```

Récupérer ensuite `categorie_produit_main.json` (scp, téléchargement, etc.)
pour l'amener là où tourne la base de `Saas`.

## 2. Vérifier/créer l'entreprise cible dans `Saas`

Les données importées seront toutes rattachées à **une** entreprise Saas.
Vérifier qu'elle existe déjà (dashboard admin `/admin/tenants/entreprise/`
ou `python manage.py shell` → `Entreprise.objects.all()`), ou la créer si
besoin.

## 3. Importer dans `Saas`

```bash
git checkout Saas
pip install -r requirements.txt   # si besoin
python manage.py migrate          # s'assurer que le schema Saas est a jour
```

D'abord en simulation, pour vérifier ce qui sera créé/ignoré sans rien
écrire en base :

```bash
python manage.py import_categorie_produit categorie_produit_main.json --entreprise "Nom exact de l'entreprise" --dry-run
```

Puis pour de vrai (sans `--dry-run`) :

```bash
python manage.py import_categorie_produit categorie_produit_main.json --entreprise "Nom exact de l'entreprise"
```

### Comportement

- **Catégories** : une catégorie `main` de nom `X` devient (ou réutilise)
  une `Categorie` `Saas` de même nom pour l'entreprise choisie.
- **Produits** : un produit dont le `libelle` existe déjà pour cette
  entreprise est **ignoré** (pas de doublon, pas d'écrasement). Un
  `codebare` déjà utilisé par un autre produit de la même entreprise est
  importé avec le code-barre laissé vide plutôt que de faire échouer
  l'import (un message l'indique).
- Le champ `special` (produits spéciaux) présent sur `main` n'existe plus
  sur le modèle `Produit` de `Saas` (remplacé par une fonctionnalité
  séparée dans une autre branche) : il n'est pas importé.
- Tout se fait dans une transaction : en cas d'erreur, rien n'est écrit.
