from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .managers import clear_current_entreprise, set_current_entreprise
from .models import Entreprise


class TenantMiddleware:
    """Résout l'entreprise courante à partir de l'utilisateur connecté.

    - Positionne request.entreprise et le thread-local associé pour la
      durée de la requête (TenantManager s'en sert pour filtrer les
      querysets).
    - Redirige les utilisateurs authentifiés sans aucune entreprise
      accessible vers une page d'erreur explicite plutôt que de les
      laisser voir un dashboard vide sans explication.
    - Un utilisateur accédant à plusieurs entreprises (superuser : toutes
      les entreprises ; utilisateur normal : son entreprise principale +
      ses entreprises additionnelles) est redirigé vers
      /tenants/choisir-entreprise/ tant qu'il n'a pas fait son choix ; ce
      choix est mémorisé dans la session. Avec une seule entreprise
      accessible, elle est utilisée directement, sans passer par cette page.
    - Si l'entreprise résolue a une date de fin de contrat dépassée, tout
      utilisateur non-superuser est redirigé vers une page d'information
      bloquante (/tenants/contrat-expire/) ; le super admin n'est jamais
      bloqué. L'alerte "contrat bientôt terminé" (J-5) est gérée à part,
      de façon non bloquante, via le context processor current_entreprise.

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
        # Tout /djomy/ (page de renouvellement, retour de paiement, webhook) doit
        # rester accessible même à une entreprise bloquée : c'est le seul moyen
        # pour elle de payer et donc de se débloquer elle-même.
        if path.startswith('/djomy/'):
            return True
        chemins_exemptes = (
            reverse('login'),
            reverse('logout'),
            reverse('compte_non_rattache'),
            reverse('choisir_entreprise'),
            reverse('contrat_expire'),
            # Outil superadmin : la cible est choisie explicitement dans le
            # formulaire, aucune "entreprise courante" n'est necessaire pour y acceder.
            reverse('importEntreprise'),
        )
        return path in chemins_exemptes

    def _contrat_expire(self, entreprise):
        return (
            entreprise.date_fin_contrat is not None
            and timezone.localdate() > entreprise.date_fin_contrat
        )

    def _entreprise_depuis_session(self, request, entreprises_autorisees):
        entreprise_id = request.session.get('entreprise_id')
        if not entreprise_id:
            return None
        entreprise = entreprises_autorisees.filter(pk=entreprise_id).first()
        if entreprise is None:
            request.session.pop('entreprise_id', None)
        return entreprise

    def _rediriger_vers_choix(self, request):
        next_url = quote(request.get_full_path())
        return redirect(f"{reverse('choisir_entreprise')}?next={next_url}")

    def __call__(self, request):
        entreprise = None
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated:
            if user.is_superuser:
                entreprises_autorisees = Entreprise.objects.all()
                entreprise = self._entreprise_depuis_session(request, entreprises_autorisees)
                if entreprise is None and not self._est_chemin_exempte(request.path):
                    return self._rediriger_vers_choix(request)
            else:
                entreprises_accessibles = user.entreprises_accessibles()
                nb_entreprises = entreprises_accessibles.count()

                if nb_entreprises == 0:
                    if not self._est_chemin_exempte(request.path):
                        return redirect('compte_non_rattache')
                elif nb_entreprises == 1:
                    entreprise = entreprises_accessibles.first()
                else:
                    entreprise = self._entreprise_depuis_session(request, entreprises_accessibles)
                    if entreprise is None and not self._est_chemin_exempte(request.path):
                        return self._rediriger_vers_choix(request)

                if (
                    entreprise is not None
                    and self._contrat_expire(entreprise)
                    and not self._est_chemin_exempte(request.path)
                ):
                    return redirect('contrat_expire')

        request.entreprise = entreprise
        set_current_entreprise(entreprise)
        try:
            response = self.get_response(request)
        finally:
            clear_current_entreprise()
        return response
