# Déploiement sur PythonAnywhere

Guide pour héberger ce projet Django (WcommercialSoft) sur PythonAnywhere.

## 1. Préparer le compte et le code

1. Créer un compte sur https://www.pythonanywhere.com (un compte payant est
   recommandé : le plan gratuit limite les hôtes sortants autorisés et
   l'espace disque).
2. Ouvrir une console **Bash** depuis le dashboard PythonAnywhere et cloner
   le dépôt :

   ```bash
   git clone https://github.com/laguisoft/wcommercialsoft.git
   cd wcommercialsoft
   git checkout claude/pythonanywhere-hosting-kx0ptr
   ```

## 2. Créer l'environnement virtuel

Le projet nécessite Python 3.10+ (Django 5.2). Dans la console Bash :

```bash
mkvirtualenv --python=/usr/bin/python3.11 wcommercialsoft-venv
pip install -r requirements.txt
```

(`mkvirtualenv` réactive automatiquement le venv aux prochaines connexions
à la console ; sinon utiliser `workon wcommercialsoft-venv`.)

## 3. Base de données MySQL

Le projet est configuré pour MySQL uniquement (voir
`WcommercialSoft/settings.py`). PythonAnywhere fournit une base MySQL
gratuite par compte :

1. Onglet **Databases** du dashboard : définir un mot de passe MySQL, puis
   créer la base (nom généralement `<utilisateur>$wcommercialsoft`).
2. Noter l'hôte MySQL affiché (ex. `<utilisateur>.mysql.pythonanywhere-services.com`).

## 4. Variables d'environnement

Le projet lit sa configuration via variables d'environnement
(`os.getenv` / `python-decouple`). Créer un fichier `.env` à la racine du
projet (non versionné, voir `.gitignore`) :

```bash
DJANGO_SECRET_KEY=une-cle-secrete-longue-et-aleatoire
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<utilisateur>.pythonanywhere.com
DJANGO_SECURE_SSL=True

DB_ENGINE=mysql
DB_NAME=<utilisateur>$wcommercialsoft
DB_USER=<utilisateur>
DB_PASSWORD=le-mot-de-passe-mysql-defini-a-l-etape-3
DB_HOST=<utilisateur>.mysql.pythonanywhere-services.com
DB_PORT=3306
```

`DB_ENGINE=mysql` est indispensable : sans cette variable, `settings.py`
utilise SQLite par défaut (pratique en local, à éviter en production).

Générer une `DJANGO_SECRET_KEY` sûre :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Migrations, fichiers statiques et superutilisateur

Toujours dans la console, venv activé :

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 6. Configurer l'application web PythonAnywhere

1. Onglet **Web** → **Add a new web app** → choisir **Manual configuration**
   (pas "Django", pour garder le contrôle sur `settings.py`) → sélectionner
   la même version de Python que le venv (3.11).
2. **Virtualenv** : renseigner le chemin, ex.
   `/home/<utilisateur>/.virtualenvs/wcommercialsoft-venv`.
3. **Code** :
   - Source code : `/home/<utilisateur>/wcommercialsoft`
   - Working directory : `/home/<utilisateur>/wcommercialsoft`
4. **WSGI configuration file** : ouvrir le fichier proposé par PythonAnywhere
   et remplacer son contenu par :

   ```python
   import os
   import sys

   path = '/home/<utilisateur>/wcommercialsoft'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WcommercialSoft.settings')

   # Charger le .env avant d'importer l'application Django
   from decouple import Config, RepositoryEnv
   env_config = Config(RepositoryEnv(os.path.join(path, '.env')))
   for key in (
       'DJANGO_SECRET_KEY', 'DJANGO_DEBUG', 'DJANGO_ALLOWED_HOSTS',
       'DJANGO_SECURE_SSL', 'DB_ENGINE', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
       'DB_HOST', 'DB_PORT',
   ):
       os.environ.setdefault(key, env_config.get(key, default=''))

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

5. **Static files** (section "Static files" de l'onglet Web) : ajouter
   - URL `/static/` → Directory `/home/<utilisateur>/wcommercialsoft/staticfiles`

## 7. Recharger l'application

Cliquer sur le bouton vert **Reload** en haut de l'onglet Web, puis ouvrir
`https://<utilisateur>.pythonanywhere.com`.

## 8. Mises à jour ultérieures

```bash
cd wcommercialsoft
git pull origin claude/pythonanywhere-hosting-kx0ptr
workon wcommercialsoft-venv
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Puis recharger l'application depuis l'onglet **Web**.
