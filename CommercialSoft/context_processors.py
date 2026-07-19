from django.core.cache import cache

# Duree courte : le badge peut afficher un compte vieux de quelques
# secondes sans consequence, mais economise une requete COUNT() sur
# chaque page vue par les utilisateurs ayant la permission add_commande.
DUREE_CACHE_DEMANDES_ATTENTE = 20


def nombre_demandes_commande_en_attente(entreprise):
    cle = f"demandes_commande_en_attente:{entreprise.id if entreprise else 'none'}"
    count = cache.get(cle)
    if count is None:
        from .models import CommandeClient
        count = CommandeClient.objects.filter(statut='En attente').count()
        cache.set(cle, count, DUREE_CACHE_DEMANDES_ATTENTE)
    return count


def demandes_commande_en_attente(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.has_perm('CommercialSoft.add_commande'):
        return {}

    count = nombre_demandes_commande_en_attente(getattr(request, 'entreprise', None))
    return {'demandes_commande_en_attente_count': count}
