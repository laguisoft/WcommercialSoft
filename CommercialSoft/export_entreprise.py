"""Export complet des donnees d'une entreprise (branche main, mono-tenant).

Produit un paquet JSON autoportant destine a etre importe plus tard dans une
entreprise (tenant) de la branche Saas via `import_entreprise`. Ne contient
jamais de mot de passe : les comptes utilisateurs sont exportes par identite
seule (username/nom/groupes), a recreer ou relier explicitement lors de
l'import.
"""
import hashlib
import json
from datetime import datetime, timezone as dt_timezone

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import serializers

FORMAT_VERSION = 1

# Ordre indicatif (les references entre objets se font par pk + "model",
# resolues par l'import quel que soit l'ordre des blocs dans le fichier).
MODELES_EXPORTES = [
    'CommercialSoft.Fournisseur',
    'CommercialSoft.Categorie',
    'CommercialSoft.Produit',
    'CommercialSoft.Livraison',
    'CommercialSoft.LivraisonProduit',
    'CommercialSoft.Societe',
    'CommercialSoft.Client',
    'CommercialSoft.ClientSpecial',
    'CommercialSoft.Commande',
    'CommercialSoft.CommandeProduit',
    'CommercialSoft.CommandeClient',
    'CommercialSoft.CommandeClientProduit',
    'CommercialSoft.Categorie_Depense',
    'CommercialSoft.Depense',
    'CommercialSoft.Categorie_Decaissement',
    'CommercialSoft.Decaissement',
    'CommercialSoft.VersementClient',
    'CommercialSoft.PretClient',
    'CommercialSoft.DetteFournisseur',
    'CommercialSoft.VersementFournisseur',
    'CommercialSoft.VersementGerant',
    'CommercialSoft.Retour',
]

UTILISATEUR_MODEL_LABEL = 'accounts.customuser'


def _cle_compteur(label):
    return label.lower()


def compter_objets():
    """Comptages rapides (COUNT) par modele, pour l'apercu avant export."""
    compteurs = {}
    for label in MODELES_EXPORTES:
        modele = apps.get_model(label)
        compteurs[_cle_compteur(label)] = modele.objects.count()
    compteurs[UTILISATEUR_MODEL_LABEL] = get_user_model().objects.count()
    return compteurs


def _serialiser_utilisateurs():
    """Serialise l'identite des utilisateurs, sans jamais inclure le mot de passe."""
    objets = []
    for user in get_user_model().objects.all().order_by('id'):
        objets.append({
            'model': UTILISATEUR_MODEL_LABEL,
            'pk': user.pk,
            'fields': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'groupes': list(user.groups.values_list('name', flat=True)),
            },
        })
    return objets


def construire_export():
    """Construit le paquet d'export complet : manifeste + tous les objets."""
    objets = []
    compteurs = {}

    for label in MODELES_EXPORTES:
        modele = apps.get_model(label)
        queryset = modele.objects.all().order_by('pk')
        objets_modele = json.loads(serializers.serialize('json', queryset))
        objets.extend(objets_modele)
        compteurs[_cle_compteur(label)] = len(objets_modele)

    utilisateurs = _serialiser_utilisateurs()
    objets.extend(utilisateurs)
    compteurs[UTILISATEUR_MODEL_LABEL] = len(utilisateurs)

    paquet = {
        'format_version': FORMAT_VERSION,
        'exporte_le': datetime.now(dt_timezone.utc).isoformat(),
        'compteurs': compteurs,
        'objets': objets,
    }

    contenu = json.dumps(paquet, ensure_ascii=False, sort_keys=True).encode('utf-8')
    paquet['empreinte_sha256'] = hashlib.sha256(contenu).hexdigest()

    return paquet


def nom_fichier_export(paquet):
    date = paquet['exporte_le'][:10]
    return f"export_entreprise_{date}.json"
