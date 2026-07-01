from django.shortcuts import redirect
from django.urls import reverse

from .managers import clear_current_entreprise, set_current_entreprise


class TenantMiddleware:
    """Résout l'entreprise courante à partir de l'utilisateur connecté.

    - Positionne request.entreprise (None si non authentifié ou superuser
      sans entreprise assignée) et le thread-local associé pour la durée
      de la requête (TenantManager s'en sert pour filtrer les querysets).
    - Redirige les utilisateurs authentifiés non-superusers sans entreprise
      vers une page d'erreur explicite plutôt que de les laisser voir un
      dashboard vide sans explication.

    Note: on compare request.path plutôt que request.resolver_match, car
    ce dernier n'est pas encore renseigné à ce stade de la chaîne de
    middlewares (il est positionné plus loin, lors de la résolution de
    l'URL qui se produit à l'intérieur de self.get_response()).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _est_chemin_exempte(self, path):
        if path.startswith('/admin/'):
            return True
        chemins_exemptes = (
            reverse('login'),
            reverse('logout'),
            reverse('compte_non_rattache'),
        )
        return path in chemins_exemptes

    def __call__(self, request):
        entreprise = None
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated:
            entreprise = getattr(user, 'entreprise', None)

            if entreprise is None and not user.is_superuser:
                if not self._est_chemin_exempte(request.path):
                    return redirect('compte_non_rattache')

        request.entreprise = entreprise
        set_current_entreprise(entreprise)
        try:
            response = self.get_response(request)
        finally:
            clear_current_entreprise()
        return response
