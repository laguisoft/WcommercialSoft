import json
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .client import DjomyClient, DjomyError
from .models import PaiementAbonnement
from .utils import ajouter_mois

logger = logging.getLogger(__name__)

DUREES_DISPONIBLES = [1, 3, 6, 12]

# Statuts définitifs : un webhook/retour ultérieur ne doit plus rien changer.
STATUTS_TERMINAUX = {'SUCCESS', 'FAILED', 'CANCELLED', 'TIMEOUT', 'REFUNDED'}


def _est_client_portail(user):
    return hasattr(user, 'client_profile')


def _nouvelle_reference(entreprise):
    return f"ABN-{entreprise.id}-{uuid.uuid4().hex[:12]}"


def _appliquer_resultat(merchant_reference, data):
    """Met à jour la tentative de paiement à partir d'une réponse Djomy (verify_payment),
    et prolonge l'abonnement de l'entreprise une seule fois, à la première confirmation SUCCESS.
    """
    with transaction.atomic():
        try:
            paiement = PaiementAbonnement.all_objects.select_for_update().get(
                merchant_reference=merchant_reference
            )
        except PaiementAbonnement.DoesNotExist:
            logger.warning("Paiement Djomy introuvable pour la référence %s", merchant_reference)
            return None

        deja_terminale = paiement.statut in STATUTS_TERMINAUX
        nouveau_statut = data.get('status') or paiement.statut

        paiement.statut = nouveau_statut
        paiement.transaction_id = data.get('transactionId') or paiement.transaction_id
        paiement.methode_paiement = data.get('paymentMethod') or paiement.methode_paiement
        paiement.reponse_brute = data
        paiement.save()

        if nouveau_statut == 'SUCCESS' and not deja_terminale:
            entreprise = paiement.entreprise
            aujourdhui = timezone.localdate()
            base = entreprise.date_fin_contrat
            if base is None or base < aujourdhui:
                base = aujourdhui
            entreprise.date_fin_contrat = ajouter_mois(base, paiement.duree_mois)
            entreprise.save(update_fields=['date_fin_contrat'])

        return paiement


@login_required
def renouveler_abonnement(request):
    if _est_client_portail(request.user):
        return redirect('commerce_dashboard')

    entreprise = getattr(request, 'entreprise', None)
    if entreprise is None:
        next_url = reverse('djomy_renouveler')
        return redirect(f"{reverse('choisir_entreprise')}?next={next_url}")

    prix_mensuel = settings.DJOMY_PRIX_MENSUEL_GNF
    durees = [{'mois': m, 'montant': m * prix_mensuel} for m in DUREES_DISPONIBLES]

    if request.method == 'POST':
        try:
            duree_mois = int(request.POST.get('duree_mois', 0))
        except ValueError:
            duree_mois = 0
        payer_number = request.POST.get('payer_number', '').strip()

        erreurs = []
        if duree_mois not in DUREES_DISPONIBLES:
            erreurs.append("Merci de choisir une durée valide.")
        if not payer_number:
            erreurs.append("Le numéro de téléphone du payeur est obligatoire.")

        if not erreurs:
            montant = duree_mois * prix_mensuel
            reference = _nouvelle_reference(entreprise)
            paiement = PaiementAbonnement.objects.create(
                entreprise=entreprise,
                duree_mois=duree_mois,
                montant=montant,
                payer_number=payer_number,
                merchant_reference=reference,
            )
            retour_url = request.build_absolute_uri(
                reverse('djomy_retour', args=[reference])
            )
            try:
                data = DjomyClient().create_payment_gateway(
                    amount=montant,
                    payer_number=payer_number,
                    country_code=settings.DJOMY_COUNTRY_CODE,
                    description=f"Renouvellement abonnement {entreprise.nom} ({duree_mois} mois)",
                    merchant_payment_reference=reference,
                    return_url=retour_url,
                    cancel_url=retour_url,
                    metadata={'entreprise_id': entreprise.id, 'duree_mois': duree_mois},
                )
            except DjomyError as exc:
                logger.error("Échec create_payment_gateway Djomy (%s) : %s", reference, exc)
                paiement.statut = 'FAILED'
                paiement.save(update_fields=['statut'])
                erreurs.append(f"Le paiement n'a pas pu être initié : {exc}")
            else:
                paiement.transaction_id = data.get('transactionId')
                paiement.statut = data.get('status', 'REDIRECTED')
                paiement.reponse_brute = data
                paiement.save()
                redirect_url = data.get('redirectUrl')
                if redirect_url:
                    return redirect(redirect_url)
                erreurs.append("Djomy n'a pas renvoyé d'URL de paiement.")

        for erreur in erreurs:
            messages.error(request, erreur)

    return render(request, 'djomy/renouveler.html', {
        'entreprise': entreprise,
        'durees': durees,
        'prix_mensuel': prix_mensuel,
    })


@login_required
def retour_paiement(request, reference):
    entreprise = getattr(request, 'entreprise', None)
    paiement = get_object_or_404(PaiementAbonnement.all_objects, merchant_reference=reference)

    if not request.user.is_superuser and paiement.entreprise_id != getattr(entreprise, 'id', None):
        return HttpResponseForbidden("Cette tentative de paiement n'appartient pas à votre entreprise.")

    if paiement.transaction_id and paiement.statut not in STATUTS_TERMINAUX:
        try:
            data = DjomyClient().verify_payment(paiement.transaction_id)
        except DjomyError as exc:
            logger.error("Échec verify_payment Djomy (%s) : %s", reference, exc)
        else:
            paiement = _appliquer_resultat(reference, data) or paiement

    return render(request, 'djomy/retour.html', {'paiement': paiement})


@csrf_exempt
@require_POST
def webhook(request):
    signature = request.headers.get('X-Webhook-Signature', '')
    client = DjomyClient()
    if not client.verify_webhook_signature(request.body, signature):
        logger.warning("Signature webhook Djomy invalide.")
        return HttpResponseForbidden("Signature invalide.")

    try:
        payload = json.loads(request.body or b'{}')
    except ValueError:
        return HttpResponse(status=400)

    event_type = payload.get('eventType')
    data = payload.get('data') or {}
    reference = data.get('merchantPaymentReference')

    if event_type == 'payment.success' and reference:
        transaction_id = data.get('transactionId')
        try:
            # Le webhook seul ne prouve rien : on reconfirme toujours auprès de Djomy.
            confirmation = client.verify_payment(transaction_id) if transaction_id else data
        except DjomyError as exc:
            logger.error("Échec verify_payment sur webhook Djomy (%s) : %s", reference, exc)
        else:
            _appliquer_resultat(reference, confirmation)
    elif reference:
        _appliquer_resultat(reference, data)

    return HttpResponse(status=200)
