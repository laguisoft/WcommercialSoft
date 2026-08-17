from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from tenants.models import Entreprise


class SynchronisationHorsLigneGlobaleTests(TestCase):
    """La synchronisation (ventes + réceptions) doit démarrer dès qu'une
    page s'affiche après connexion, pas seulement quand l'utilisateur ouvre
    la page de vente ou de réception. offline-core.js doit donc être chargé
    sur toute page qui étend starter-page.html, y compris celles qui
    redéfinissent le bloc js (ex. reception2.html)."""

    def setUp(self):
        User = get_user_model()
        self.entreprise = Entreprise.objects.create(nom="Boutique Sync", ville="Conakry")
        self.user = User.objects.create_user(username="gerant_sync", password="secret123", entreprise=self.entreprise)
        groupe_admin, _ = Group.objects.get_or_create(name="Administrateur")
        self.user.groups.add(groupe_admin)
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_livraison", "add_livraisonproduit"]
        ))
        self.client.login(username="gerant_sync", password="secret123")

    def test_offline_core_charge_sur_le_dashboard(self):
        response = self.client.get(reverse('commerce_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "js/offline-core.js")
        self.assertContains(response, "window.CSRF_TOKEN")

    def test_offline_core_charge_sur_reception_malgre_le_bloc_js_redefini(self):
        response = self.client.get(reverse('commerce_reception'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "js/offline-core.js")
        self.assertContains(response, 'id="etatSynchroReception"')

    def test_page_vente_conserve_son_propre_declencheur(self):
        response = self.client.get(reverse('commerce_vente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "js/offline-core.js")
        self.assertContains(response, 'id="etatSynchro"')
