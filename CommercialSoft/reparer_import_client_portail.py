"""Repare les Client importes vers Saas AVANT le correctif du lien vers leur
compte portail (Client.user) : voir import_entreprise.py, qui ne relie
desormais plus jamais un Client importe sans restaurer ce lien.

Reutilise le MEME fichier JSON que celui deja utilise pour import_entreprise
(il contient encore, pour chaque commercialsoft.client, l'ancien pk du
compte portail et, dans les objets accounts.customuser, le username qui lui
correspondait a l'export).

Cas traite automatiquement : le compte portail a ete recree cote Saas avec
le meme nom d'utilisateur qu'avant (option --creer de import_entreprise,
le cas normal pour un client qui n'existait pas encore dans Saas). Les
autres cas (le compte a ete relie a un compte Saas existant d'un nom
different, via --lier) doivent etre indiques explicitement par l'operateur.
"""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Client


def _index_usernames(paquet):
    """Ancien pk (accounts.customuser) -> username, tel qu'a l'export."""
    return {
        obj['pk']: obj['fields']['username']
        for obj in paquet.get('objets', [])
        if obj['model'].lower() == 'accounts.customuser'
    }


def _clients_avec_compte_portail(paquet):
    return [
        obj for obj in paquet.get('objets', [])
        if obj['model'].lower() == 'commercialsoft.client' and obj['fields'].get('user')
    ]


def analyser_reparation(paquet, entreprise):
    """Dry-run : pour chaque Client du paquet ayant eu un compte portail,
    indique s'il est deja relie, resolu automatiquement (meme username cote
    Saas), introuvable, ou ambigu (necessite --lier NOM_CLIENT:username)."""
    usernames = _index_usernames(paquet)
    User = get_user_model()
    rapport = {'deja_lies': [], 'resolus': [], 'introuvables': [], 'ambigus': []}

    for obj in _clients_avec_compte_portail(paquet):
        f = obj['fields']
        client = Client.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if not client:
            rapport['introuvables'].append(f['nom'])
            continue
        if client.user_id:
            rapport['deja_lies'].append(f['nom'])
            continue

        ancien_username = usernames.get(f['user'])
        candidat = (
            User.objects.filter(username=ancien_username, entreprise=entreprise).first()
            if ancien_username else None
        )
        if candidat:
            rapport['resolus'].append({'client': f['nom'], 'username': candidat.username, 'user_id': candidat.id})
        else:
            rapport['ambigus'].append({'client': f['nom'], 'ancien_username': ancien_username})

    return rapport


def _resoudre_cible(valeur, entreprise):
    User = get_user_model()
    if str(valeur).isdigit():
        return User.objects.filter(pk=int(valeur), entreprise=entreprise).first()
    return User.objects.filter(username=valeur, entreprise=entreprise).first()


@transaction.atomic
def executer_reparation(paquet, entreprise, overrides=None):
    """Relie chaque Client resolu automatiquement, plus ceux fournis
    explicitement dans `overrides` (nom_client -> username ou id Saas).
    Ne touche jamais un Client qui a deja un compte portail relie."""
    overrides = overrides or {}
    usernames = _index_usernames(paquet)
    User = get_user_model()
    rapport = {'lies': [], 'ignores': []}

    for obj in _clients_avec_compte_portail(paquet):
        f = obj['fields']
        client = Client.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if not client or client.user_id:
            continue

        if f['nom'] in overrides:
            cible = _resoudre_cible(overrides[f['nom']], entreprise)
        else:
            ancien_username = usernames.get(f['user'])
            cible = (
                User.objects.filter(username=ancien_username, entreprise=entreprise).first()
                if ancien_username else None
            )

        if cible:
            client.user = cible
            client.save(update_fields=['user'])
            rapport['lies'].append(f['nom'])
        else:
            rapport['ignores'].append(f['nom'])

    return rapport
