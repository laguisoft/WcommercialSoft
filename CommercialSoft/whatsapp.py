"""Aide a la construction de liens WhatsApp ("Cliquer pour discuter") pour
l'envoi manuel des factures/recus en piece jointe.
"""
import re
from urllib.parse import quote

from django.conf import settings


def format_whatsapp_number(telephone):
    """Normalise un numero de telephone local au format attendu par wa.me
    (indicatif pays + numero, chiffres uniquement). Retourne None si le
    numero est vide ou invalide."""
    if not telephone:
        return None

    chiffres = re.sub(r'\D', '', telephone)
    if not chiffres:
        return None

    indicatif = str(settings.WHATSAPP_COUNTRY_CODE)
    if chiffres.startswith(indicatif):
        return chiffres
    if chiffres.startswith('0'):
        chiffres = chiffres[1:]
    return indicatif + chiffres if chiffres else None


def build_whatsapp_link(telephone, message=""):
    """Construit un lien https://wa.me/... pre-rempli avec un message.
    Retourne None si le numero est invalide."""
    numero = format_whatsapp_number(telephone)
    if not numero:
        return None
    return f"https://wa.me/{numero}?text={quote(message)}"
