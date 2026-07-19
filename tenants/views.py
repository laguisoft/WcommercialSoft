from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Entreprise


@login_required
def compte_non_rattache(request):
    return render(request, 'tenants/compte_non_rattache.html')


def _redirection_sure(request, next_url, defaut):
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return defaut


@login_required
@user_passes_test(lambda u: u.is_superuser)
def choisir_entreprise(request):
    next_url = request.GET.get('next') or request.POST.get('next', '')

    if request.method == 'POST':
        entreprise = get_object_or_404(Entreprise, pk=request.POST.get('entreprise_id'))
        request.session['entreprise_id'] = entreprise.id
        return redirect(_redirection_sure(request, next_url, reverse('commerce_dashboard')))

    q = request.GET.get('q', '').strip()
    entreprises = Entreprise.objects.all().order_by('nom')
    if q:
        entreprises = entreprises.filter(
            Q(nom__icontains=q) | Q(ville__icontains=q) | Q(proprietaire__icontains=q)
        )

    return render(request, 'tenants/choisir_entreprise.html', {
        'entreprises': entreprises,
        'q': q,
        'next': next_url,
    })
