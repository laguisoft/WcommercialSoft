from django import template
from django.utils.html import format_html

from CommercialSoft.whatsapp import build_whatsapp_link

register = template.Library()


@register.filter
def whatsapp_url(telephone, message=""):
    """Usage: {{ client.telephone|whatsapp_url:message }}
    Retourne un lien wa.me pret a l'emploi, ou une chaine vide si le
    numero est invalide (le template peut alors masquer le bouton)."""
    return build_whatsapp_link(telephone, message) or ""


def _message_facture(client_nom, facture_id, montant):
    if montant is not None:
        return f"Bonjour {client_nom}, voici votre facture n°{facture_id} d'un montant de {montant} GNF."
    return f"Bonjour {client_nom}, voici votre facture n°{facture_id}."


@register.simple_tag
def whatsapp_facture_link(telephone, client_nom="", facture_id="", montant=None):
    """Usage: {% whatsapp_facture_link client.telephone client.nom facture.id facture.montant as wa_link %}
    Retourne un lien wa.me pret a l'emploi (chaine vide si le numero est
    invalide) pour un bouton/lien personnalise dans le template appelant."""
    return build_whatsapp_link(telephone, _message_facture(client_nom, facture_id, montant)) or ""


@register.simple_tag
def whatsapp_facture_button(telephone, client_nom="", facture_id="", montant=None):
    """Usage: {% whatsapp_facture_button client.telephone client.nom facture.id facture.montant %}
    Rend un lien "Envoyer via WhatsApp" pret a etre insere dans un menu
    deroulant ; rend une chaine vide si le client n'a pas de numero valide."""
    lien = build_whatsapp_link(telephone, _message_facture(client_nom, facture_id, montant))
    if not lien:
        return ""
    return format_html(
        '<a class="dropdown-item" target="_blank" href="{}" title="Envoyer via WhatsApp">'
        '<i class="fab fa-whatsapp text-success"></i> Envoyer via WhatsApp</a>',
        lien,
    )
