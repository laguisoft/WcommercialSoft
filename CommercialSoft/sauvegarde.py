"""Sauvegarde et restauration de TOUTE la base SaaS (toutes les entreprises,
comptes utilisateurs compris), réservées au super-administrateur.

Format du fichier (.json.gz) :
    {"format": "wcs-saas-sauvegarde", "version": 1, "cree_le": "...",
     "migrations": [[app, nom], ...], "objets": [...sortie de dumpdata...]}

- Les tables techniques recréées par Django (types de contenu, permissions,
  sessions) ne sont pas sauvegardées ; les références vers elles utilisent
  leurs clés naturelles, donc la sauvegarde se recharge sur un autre serveur.
- Les identifiants (pk) sont conservés : les liens entre objets restent
  exacts et les utilisateurs gardent leur mot de passe (chiffré).
- La restauration remplace toutes les données dans UNE transaction : si la
  moindre ligne échoue, rien n'est modifié.

Ne concerne pas l'import « depuis main » (import_entreprise.py), qui reste
un import fusionné vers une seule entreprise.
"""
import gzip
import io
import json
import os

from django.apps import apps
from django.core.management import call_command
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

FORMAT = "wcs-saas-sauvegarde"
VERSION = 1

# Tables techniques recréées automatiquement par Django (migrate / post_migrate)
EXCLUS_APPS = {'contenttypes', 'sessions'}
EXCLUS_MODELES = {'auth.permission'}


class SauvegardeInvalide(Exception):
    pass


def _modele_inclus(modele):
    meta = modele._meta
    return meta.app_label not in EXCLUS_APPS and meta.label_lower not in EXCLUS_MODELES


def _modeles_sauvegardes():
    """Modèles concernés, tables de liaison many-to-many automatiques comprises."""
    return [m for m in apps.get_models(include_auto_created=True) if _modele_inclus(m)]


def _migrations_appliquees():
    return sorted(MigrationRecorder.Migration.objects.values_list('app', 'name'))


def exporter(chemin):
    """Écrit la sauvegarde complète de la base dans le fichier .json.gz `chemin`."""
    tampon = io.StringIO()
    call_command(
        'dumpdata',
        exclude=sorted(EXCLUS_APPS | EXCLUS_MODELES),
        use_natural_foreign_keys=True,
        use_base_manager=True,  # sinon TenantManager ne garderait que l'entreprise courante
        stdout=tampon,
    )
    entete = {
        'format': FORMAT,
        'version': VERSION,
        'cree_le': timezone.now().isoformat(),
        'migrations': _migrations_appliquees(),
    }
    debut = json.dumps(entete, ensure_ascii=False)[:-1]  # sans l'accolade finale
    with gzip.open(chemin, 'wt', encoding='utf-8') as f:
        f.write(debut)
        f.write(', "objets": ')
        f.write(tampon.getvalue().strip() or '[]')
        f.write('}')


def lire(chemin):
    """Lit et vérifie un fichier de sauvegarde (.json.gz ou .json)."""
    try:
        with open(chemin, 'rb') as brut:
            compresse = brut.read(2) == b'\x1f\x8b'
        ouvrir = gzip.open if compresse else open
        with ouvrir(chemin, 'rt', encoding='utf-8') as f:
            contenu = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, EOFError):
        raise SauvegardeInvalide("Fichier illisible : ce n'est pas une sauvegarde valide.")
    if not isinstance(contenu, dict) or contenu.get('format') != FORMAT:
        raise SauvegardeInvalide(
            "Ce fichier n'est pas une sauvegarde de la base SaaS "
            "(pour un export de la branche main, utilisez « Importer les données d'un client (main) »)."
        )
    if contenu.get('version') != VERSION or not isinstance(contenu.get('objets'), list):
        raise SauvegardeInvalide("Version de sauvegarde non prise en charge.")
    return contenu


def migrations_manquantes(sauvegarde):
    """Migrations présentes dans la sauvegarde mais pas appliquées ici : la
    sauvegarde vient d'une version plus récente de l'application."""
    ici = set(_migrations_appliquees())
    return sorted({tuple(m) for m in sauvegarde.get('migrations', [])} - ici)


def resume(sauvegarde):
    """Nombre d'objets par modèle, pour l'écran de confirmation."""
    compteurs = {}
    for obj in sauvegarde['objets']:
        compteurs[obj.get('model', '?')] = compteurs.get(obj.get('model', '?'), 0) + 1
    return sorted(compteurs.items())


def restaurer(sauvegarde, dossier_temp):
    """Remplace TOUTES les données de la base par celles de la sauvegarde.
    Transaction unique : en cas d'erreur, la base reste comme avant."""
    manquantes = migrations_manquantes(sauvegarde)
    if manquantes:
        raise SauvegardeInvalide(
            "Cette sauvegarde vient d'une version plus récente de l'application "
            f"({len(manquantes)} migration(s) absente(s) ici). Mettez le serveur à jour "
            "(git pull puis python manage.py migrate) avant de la restaurer."
        )

    os.makedirs(dossier_temp, exist_ok=True)
    fixture = os.path.join(dossier_temp, f"wcs_restauration_{os.getpid()}.json")
    with open(fixture, 'w', encoding='utf-8') as f:
        json.dump(sauvegarde['objets'], f)
    try:
        with transaction.atomic():
            with connection.constraint_checks_disabled():
                with connection.cursor() as curseur:
                    for modele in _modeles_sauvegardes():
                        curseur.execute(f"DELETE FROM {connection.ops.quote_name(modele._meta.db_table)}")
            call_command('loaddata', fixture, verbosity=0)
    finally:
        if os.path.exists(fixture):
            os.remove(fixture)


def sauvegarde_de_securite(dossier, garder=3):
    """Sauvegarde automatique de la base actuelle avant une restauration,
    pour pouvoir revenir en arrière. Garde les `garder` plus récentes."""
    os.makedirs(dossier, exist_ok=True)
    nom = f"avant_restauration_{timezone.localtime():%Y%m%d_%H%M%S}.json.gz"
    chemin = os.path.join(dossier, nom)
    try:
        exporter(chemin)
    except Exception:
        if os.path.exists(chemin):
            os.remove(chemin)
        raise
    anciennes = sorted(
        (n for n in os.listdir(dossier) if n.startswith('avant_restauration_')),
        reverse=True,
    )
    for ancien in anciennes[garder:]:
        try:
            os.remove(os.path.join(dossier, ancien))
        except OSError:
            pass
    return chemin


def copier_televersement(fichier, chemin):
    """Enregistre un fichier téléversé (UploadedFile) sur le disque."""
    with open(chemin, 'wb') as sortie:
        for morceau in fichier.chunks():
            sortie.write(morceau)

