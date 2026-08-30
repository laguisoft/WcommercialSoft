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
from django.db.models import Max, Min

FORMAT_VERSION = 1

# Taille au-dela de laquelle export_entreprise bascule automatiquement sur un
# export decoupe par mois (evite une erreur '413 Request Entity Too Large' au
# moment de l'upload du fichier dans l'ecran d'import de Saas).
SEUIL_DECOUPAGE_MO_DEFAUT = 8

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
    'CommercialSoft.InfoBoutique',
    'CommercialSoft.Retour',
]

# Donnees "de reference" : peu nombreuses, incluses en entier dans chaque
# fichier quand l'export est decoupe (reutilisees telles quelles a l'import,
# jamais dupliquees grace au rattachement par nom deja fait par
# import_entreprise sur Saas).
MODELES_REFERENCE = [
    'CommercialSoft.Fournisseur',
    'CommercialSoft.Categorie',
    'CommercialSoft.Produit',
    'CommercialSoft.Societe',
    'CommercialSoft.Client',
    'CommercialSoft.ClientSpecial',
    'CommercialSoft.InfoBoutique',
]

# Donnees "historiques" : potentiellement volumineuses (des annees de
# ventes), reparties par mois calendaire quand l'export est decoupe. Valeur :
# le champ de date a utiliser pour le filtrage, en remontant jusqu'au modele
# parent quand la ligne n'a pas sa propre date (pour rester garantie dans le
# meme fichier que sa commande/livraison/demande).
CHAMP_DATE_PERIODIQUE = {
    'CommercialSoft.Livraison': 'date',
    'CommercialSoft.LivraisonProduit': 'livraison__date',
    'CommercialSoft.Commande': 'date',
    'CommercialSoft.CommandeProduit': 'commande__date',
    'CommercialSoft.CommandeClient': 'date',
    'CommercialSoft.CommandeClientProduit': 'demande__date',
    'CommercialSoft.Depense': 'date',
    'CommercialSoft.Decaissement': 'date',
    'CommercialSoft.VersementClient': 'date',
    'CommercialSoft.PretClient': 'date',
    'CommercialSoft.DetteFournisseur': 'date',
    'CommercialSoft.VersementFournisseur': 'date',
    'CommercialSoft.VersementGerant': 'date',
    'CommercialSoft.Retour': 'date',
}

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


def taille_octets(paquet):
    """Taille reelle du paquet une fois serialise (indent inclus, comme le
    fichier ecrit sur disque), pour decider s'il faut decouper l'export."""
    return len(json.dumps(paquet, ensure_ascii=False, indent=2).encode('utf-8'))


def _mois_suivant(jour):
    if jour.month == 12:
        return jour.replace(year=jour.year + 1, month=1, day=1)
    return jour.replace(month=jour.month + 1, day=1)


def _bornes_dates_periodiques():
    """Plus ancienne et plus recente date parmi toutes les donnees
    periodiques. None, None si l'entreprise n'a aucune donnee periodique."""
    dates = []
    for label, champ in CHAMP_DATE_PERIODIQUE.items():
        modele = apps.get_model(label)
        agrege = modele.objects.aggregate(mn=Min(champ), mx=Max(champ))
        for valeur in (agrege['mn'], agrege['mx']):
            if valeur is not None:
                dates.append(valeur.date() if hasattr(valeur, 'date') else valeur)
    if not dates:
        return None, None
    return min(dates), max(dates)


def _periodes_mensuelles(debut, fin):
    """Liste de bornes [debut_mois, debut_mois_suivant) couvrant [debut, fin]."""
    periodes = []
    curseur = debut.replace(day=1)
    while curseur <= fin:
        suivant = _mois_suivant(curseur)
        periodes.append((curseur, suivant))
        curseur = suivant
    return periodes


def _objets_et_compteurs_reference():
    objets = []
    compteurs = {}
    for label in MODELES_REFERENCE:
        modele = apps.get_model(label)
        queryset = modele.objects.all().order_by('pk')
        objets_modele = json.loads(serializers.serialize('json', queryset))
        objets.extend(objets_modele)
        compteurs[_cle_compteur(label)] = len(objets_modele)
    return objets, compteurs


def _finaliser_paquet_lot(objets, compteurs, index, total, periode=None):
    paquet = {
        'format_version': FORMAT_VERSION,
        'exporte_le': datetime.now(dt_timezone.utc).isoformat(),
        'lot': {'index': index, 'total': total},
        'compteurs': compteurs,
        'objets': objets,
    }
    if periode:
        paquet['periode'] = {'debut': periode[0].isoformat(), 'fin': periode[1].isoformat()}
    contenu = json.dumps(paquet, ensure_ascii=False, sort_keys=True).encode('utf-8')
    paquet['empreinte_sha256'] = hashlib.sha256(contenu).hexdigest()
    return paquet


def construire_exports_mensuels():
    """Construit l'export decoupe en plusieurs paquets : un par mois
    calendaire pour les donnees historiques (ventes, depenses, ...), les
    donnees de reference (produits, clients, ...) et les utilisateurs etant
    repetes en entier dans chaque paquet. A utiliser quand un export en un
    seul fichier depasse la limite de taille acceptee par le serveur (erreur
    413 a l'upload)."""
    objets_reference, compteurs_reference = _objets_et_compteurs_reference()
    utilisateurs = _serialiser_utilisateurs()

    def compteurs_base():
        c = dict(compteurs_reference)
        c[UTILISATEUR_MODEL_LABEL] = len(utilisateurs)
        return c

    debut, fin = _bornes_dates_periodiques()
    if debut is None:
        # Aucune donnee historique : un seul paquet (reference + utilisateurs).
        return [_finaliser_paquet_lot(objets_reference + utilisateurs, compteurs_base(), 1, 1)]

    periodes = _periodes_mensuelles(debut, fin)
    paquets = []
    for debut_periode, fin_periode in periodes:
        objets = list(objets_reference) + list(utilisateurs)
        compteurs = compteurs_base()

        for label, champ in CHAMP_DATE_PERIODIQUE.items():
            modele = apps.get_model(label)
            queryset = modele.objects.filter(**{
                f"{champ}__gte": debut_periode,
                f"{champ}__lt": fin_periode,
            }).order_by('pk')
            objets_modele = json.loads(serializers.serialize('json', queryset))
            objets.extend(objets_modele)
            compteurs[_cle_compteur(label)] = len(objets_modele)

        total_periodique = sum(compteurs[_cle_compteur(l)] for l in CHAMP_DATE_PERIODIQUE)
        if total_periodique == 0 and len(periodes) > 1:
            continue  # mois sans aucune donnee : pas la peine d'un fichier a part

        paquets.append((debut_periode, fin_periode, objets, compteurs))

    if not paquets:
        return [_finaliser_paquet_lot(objets_reference + utilisateurs, compteurs_base(), 1, 1)]

    total = len(paquets)
    return [
        _finaliser_paquet_lot(objets, compteurs, index, total, periode=(debut_periode, fin_periode))
        for index, (debut_periode, fin_periode, objets, compteurs) in enumerate(paquets, start=1)
    ]


def nom_fichier_export_lot(paquet):
    date = paquet['exporte_le'][:10]
    index = paquet['lot']['index']
    total = paquet['lot']['total']
    return f"export_entreprise_{date}_lot{index:02d}-sur-{total:02d}.json"
