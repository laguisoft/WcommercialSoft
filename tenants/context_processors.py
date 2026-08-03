from django.utils import timezone


def current_entreprise(request):
    entreprise = getattr(request, 'entreprise', None)
    alerte_fin_contrat = None

    if entreprise is not None and entreprise.date_fin_contrat is not None:
        jours_restants = (entreprise.date_fin_contrat - timezone.localdate()).days
        if 0 <= jours_restants <= 5:
            alerte_fin_contrat = {
                'jours_restants': jours_restants,
                'date_fin_contrat': entreprise.date_fin_contrat,
            }

    return {
        'current_entreprise': entreprise,
        'alerte_fin_contrat': alerte_fin_contrat,
    }
