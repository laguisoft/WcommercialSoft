def demandes_commande_en_attente(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.has_perm('CommercialSoft.add_commande'):
        return {}

    from .models import CommandeClient
    count = CommandeClient.objects.filter(statut='En attente').count()
    return {'demandes_commande_en_attente_count': count}
