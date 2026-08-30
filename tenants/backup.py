"""Sauvegarde complete des donnees d'une entreprise (tenant) avant suppression.

La suppression d'une Entreprise entraine, via on_delete=CASCADE, la
suppression de TOUTES les donnees metier qui lui sont rattachees (tout ce
qui herite de TenantScopedModel, dans quelque app que ce soit). Ce module
construit et ecrit sur disque une sauvegarde JSON complete avant que cette
suppression n'ait lieu, pour qu'une suppression accidentelle ou mal jugee
reste recuperable.
"""
import json
import os
from datetime import datetime, timezone as dt_timezone

from django.apps import apps
from django.conf import settings
from django.core import serializers

from .models import TenantScopedModel

DOSSIER_SAUVEGARDES = os.path.join(settings.BASE_DIR, 'sauvegardes_entreprises')


def modeles_scopes_par_entreprise():
    """Tous les modeles heritant de TenantScopedModel, dans toutes les apps
    installees (decouverte automatique : pas besoin de maintenir une liste
    a jour a chaque nouveau modele metier)."""
    return [
        modele for modele in apps.get_models()
        if issubclass(modele, TenantScopedModel) and not modele._meta.abstract
    ]


def compter_donnees_entreprise(entreprise):
    """Comptages rapides (COUNT), pour l'apercu avant suppression."""
    compteurs = {}
    for modele in modeles_scopes_par_entreprise():
        label = f"{modele._meta.app_label}.{modele._meta.model_name}".lower()
        # all_objects (pas objects) : on ne veut jamais que le filtrage
        # automatique par "entreprise courante" (TenantManager) se combine
        # avec le filtre explicite ci-dessous.
        compteurs[label] = modele.all_objects.filter(entreprise=entreprise).count()
    return compteurs


def construire_sauvegarde(entreprise):
    """Construit le paquet JSON complet : tout ce qui sera supprime en
    cascade, plus les comptes utilisateurs qui seront detaches (pas
    supprimes, juste rendus 'non rattaches' — CustomUser.entreprise est en
    SET_NULL, pas CASCADE)."""
    objets = []
    compteurs = {}

    for modele in modeles_scopes_par_entreprise():
        label = f"{modele._meta.app_label}.{modele._meta.model_name}".lower()
        queryset = modele.all_objects.filter(entreprise=entreprise).order_by('pk')
        objets_modele = json.loads(serializers.serialize('json', queryset))
        objets.extend(objets_modele)
        compteurs[label] = len(objets_modele)

    User = apps.get_model(settings.AUTH_USER_MODEL)
    utilisateurs_detaches = list(
        User.objects.filter(entreprise=entreprise).values_list('username', flat=True)
    )
    utilisateurs_additionnels_retires = list(
        User.objects.filter(entreprises_additionnelles=entreprise).values_list('username', flat=True)
    )

    return {
        'format_version': 1,
        'sauvegarde_le': datetime.now(dt_timezone.utc).isoformat(),
        'entreprise': {
            'nom': entreprise.nom,
            'slug': entreprise.slug,
            'ville': entreprise.ville,
            'emplacement': entreprise.emplacement,
            'telephone': entreprise.telephone,
            'email': entreprise.email,
            'proprietaire': entreprise.proprietaire,
            'date_creation': entreprise.date_creation.isoformat() if entreprise.date_creation else None,
            'date_fin_contrat': entreprise.date_fin_contrat.isoformat() if entreprise.date_fin_contrat else None,
        },
        # Ces comptes ne sont pas supprimes (SET_NULL) : juste informatif,
        # pour savoir qui se retrouvera "non rattache" apres coup.
        'utilisateurs_detaches_non_supprimes': utilisateurs_detaches,
        'utilisateurs_additionnels_retires': utilisateurs_additionnels_retires,
        'compteurs': compteurs,
        'objets': objets,
    }


def nom_fichier_sauvegarde(paquet, entreprise):
    horodatage = paquet['sauvegarde_le'].replace(':', '-')
    return f"{entreprise.slug}_{horodatage}.json"


def sauvegarder_sur_disque(paquet, entreprise):
    """Ecrit le paquet sur disque, hors MEDIA_ROOT (jamais servi publiquement).
    Retourne le chemin absolu du fichier ecrit."""
    os.makedirs(DOSSIER_SAUVEGARDES, exist_ok=True)
    chemin = os.path.join(DOSSIER_SAUVEGARDES, nom_fichier_sauvegarde(paquet, entreprise))
    with open(chemin, 'w', encoding='utf-8') as fichier:
        json.dump(paquet, fichier, ensure_ascii=False, indent=2)
    return chemin
