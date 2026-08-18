import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from CommercialSoft.decorators import superadmin_required

from .backup import compter_donnees_entreprise, construire_sauvegarde, nom_fichier_sauvegarde, sauvegarder_sur_disque
from .models import Entreprise


@login_required
def compte_non_rattache(request):
    return render(request, 'tenants/compte_non_rattache.html')


@login_required
def contrat_expire(request):
    entreprise = getattr(request, 'entreprise', None)
    return render(request, 'tenants/contrat_expire.html', {'entreprise': entreprise})


def _redirection_sure(request, next_url, defaut):
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return defaut


@login_required
def choisir_entreprise(request):
    if request.user.is_superuser:
        entreprises_autorisees = Entreprise.objects.all()
    else:
        entreprises_autorisees = request.user.entreprises_accessibles()
        if entreprises_autorisees.count() < 2:
            # Rien a choisir : le middleware se charge de router vers la
            # bonne page (dashboard si une seule entreprise, compte non
            # rattache si aucune).
            return redirect('commerce_dashboard')

    next_url = request.GET.get('next') or request.POST.get('next', '')

    if request.method == 'POST':
        entreprise = get_object_or_404(entreprises_autorisees, pk=request.POST.get('entreprise_id'))
        request.session['entreprise_id'] = entreprise.id
        return redirect(_redirection_sure(request, next_url, reverse('commerce_dashboard')))

    q = request.GET.get('q', '').strip()
    entreprises = entreprises_autorisees.order_by('nom')
    if q:
        entreprises = entreprises.filter(
            Q(nom__icontains=q) | Q(ville__icontains=q) | Q(proprietaire__icontains=q)
        )

    return render(request, 'tenants/choisir_entreprise.html', {
        'entreprises': entreprises,
        'q': q,
        'next': next_url,
    })


@superadmin_required
def supprimer_entreprise(request, entreprise_id):
    """Suppression d'une entreprise (tenant), avec sauvegarde automatique de
    toutes ses donnees avant suppression et confirmation renforcee (le nom
    exact de l'entreprise doit etre saisi). La suppression est irreversible
    et entraine, en cascade, la perte de toute donnee metier rattachee
    (TenantScopedModel) ; seuls les comptes utilisateurs survivent, detaches."""
    entreprise = get_object_or_404(Entreprise, pk=entreprise_id)

    if request.method == 'POST':
        nom_saisi = request.POST.get('nom_confirmation', '').strip()
        if nom_saisi != entreprise.nom:
            messages.error(
                request,
                "Le nom saisi ne correspond pas exactement au nom de l'entreprise. "
                "Rien n'a ete supprime.",
            )
            return redirect('supprimer_entreprise', entreprise_id=entreprise.id)

        # La sauvegarde est construite et ecrite AVANT toute suppression : si
        # l'ecriture disque echoue, l'exception remonte et rien n'est
        # supprime (aucune atomicite a coder pour ca, c'est l'ordre des
        # instructions qui le garantit).
        paquet = construire_sauvegarde(entreprise)
        chemin_disque = sauvegarder_sur_disque(paquet, entreprise)
        nom_fichier = nom_fichier_sauvegarde(paquet, entreprise)

        with transaction.atomic():
            entreprise.delete()

        contenu = json.dumps(paquet, ensure_ascii=False, indent=2)
        response = HttpResponse(contenu, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
        response['X-Sauvegarde-Serveur'] = chemin_disque
        return response

    compteurs = compter_donnees_entreprise(entreprise)
    return render(request, 'tenants/supprimer_entreprise.html', {
        'entreprise': entreprise,
        'compteurs': sorted(compteurs.items()),
        'total': sum(compteurs.values()),
    })
