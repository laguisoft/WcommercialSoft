import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .views import utilisateur_de_entreprise, utilisateurs_de_entreprise
from tenants.models import Entreprise


class UtilisateurDeEntrepriseTests(TestCase):
    """CustomUser n'est pas un TenantScopedModel (login partage par tout le
    Saas) : ces helpers doivent etre le seul point de resolution d'un
    utilisateur a partir d'un id fourni par le client, pour ne jamais
    exposer/filtrer par un compte d'une autre entreprise."""

    def setUp(self):
        User = get_user_model()
        self.entreprise_a = Entreprise.objects.create(nom="Boutique A", ville="Conakry")
        self.entreprise_b = Entreprise.objects.create(nom="Boutique B", ville="Kankan")
        self.vendeur_a = User.objects.create_user(username="vendeur_a", password="x", entreprise=self.entreprise_a)
        self.vendeur_b = User.objects.create_user(username="vendeur_b", password="x", entreprise=self.entreprise_b)

    def test_utilisateur_de_entreprise_refuse_un_id_dune_autre_entreprise(self):
        request = type('R', (), {'entreprise': self.entreprise_a})()
        self.assertIsNone(utilisateur_de_entreprise(request, self.vendeur_b.id))
        self.assertEqual(utilisateur_de_entreprise(request, self.vendeur_a.id), self.vendeur_a)

    def test_utilisateur_de_entreprise_sans_entreprise_resolue_renvoie_none(self):
        request = type('R', (), {'entreprise': None})()
        self.assertIsNone(utilisateur_de_entreprise(request, self.vendeur_a.id))

    def test_utilisateur_de_entreprise_id_invalide_renvoie_none(self):
        request = type('R', (), {'entreprise': self.entreprise_a})()
        self.assertIsNone(utilisateur_de_entreprise(request, "n'importe quoi"))
        self.assertIsNone(utilisateur_de_entreprise(request, None))

    def test_utilisateurs_de_entreprise_exclut_les_autres_entreprises(self):
        request = type('R', (), {'entreprise': self.entreprise_a})()
        noms = set(utilisateurs_de_entreprise(request).values_list('username', flat=True))
        self.assertIn('vendeur_a', noms)
        self.assertNotIn('vendeur_b', noms)

    def test_utilisateurs_de_entreprise_inclut_les_entreprises_additionnelles(self):
        self.vendeur_b.entreprises_additionnelles.add(self.entreprise_a)
        request = type('R', (), {'entreprise': self.entreprise_a})()
        noms = set(utilisateurs_de_entreprise(request).values_list('username', flat=True))
        self.assertIn('vendeur_b', noms)


class RechercheVenteTenantScopingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.entreprise_a = Entreprise.objects.create(nom="Boutique C", ville="Labe")
        self.entreprise_b = Entreprise.objects.create(nom="Boutique D", ville="Mamou")
        self.vendeur_a = User.objects.create_user(username="vendeur_c", password="secret123", entreprise=self.entreprise_a)
        self.vendeur_b = User.objects.create_user(username="vendeur_d", password="secret123", entreprise=self.entreprise_b)
        self.vendeur_a.user_permissions.add(*self._permissions())
        self.client.login(username="vendeur_c", password="secret123")

    @staticmethod
    def _permissions():
        from django.contrib.auth.models import Permission
        return Permission.objects.filter(codename__in=["view_commande", "view_versementgerant"])

    def test_recherche_vente_refuse_un_utilisateur_dune_autre_entreprise(self):
        response = self.client.post(reverse('rechercheVente'), data={
            'idUser': self.vendeur_b.id, 'dateDebut': '', 'dateFin': '',
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], "Utilisateur introuvable")

    def test_recherche_vente_accepte_un_utilisateur_de_la_meme_entreprise(self):
        response = self.client.post(reverse('rechercheVente'), data={
            'idUser': self.vendeur_a.id, 'dateDebut': '', 'dateFin': '',
        })
        self.assertEqual(response.status_code, 200)

    def test_dropdown_produit_vendu_nexpose_pas_les_utilisateurs_dune_autre_entreprise(self):
        response = self.client.get(reverse('commerce_produitVendu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{self.vendeur_a.id}"')
        self.assertNotContains(response, f'value="{self.vendeur_b.id}"')

    def test_recherche_versementGerant_refuse_un_utilisateur_dune_autre_entreprise(self):
        response = self.client.post(reverse('commerce_rechercheVersementGerant'), data={
            'idGerant': self.vendeur_b.id, 'dateDebut': '2026-01-01', 'dateFin': '2026-12-31',
        })
        self.assertEqual(response.status_code, 404)


class SyncVentesTenantScopingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.entreprise_a = Entreprise.objects.create(nom="Boutique E", ville="Boke")
        self.entreprise_b = Entreprise.objects.create(nom="Boutique F", ville="Kindia")
        self.vendeur_a = User.objects.create_user(username="vendeur_e", password="secret123", entreprise=self.entreprise_a)
        self.vendeur_b = User.objects.create_user(username="vendeur_f", password="secret123", entreprise=self.entreprise_b)
        from .models import Categorie, Produit
        self.categorie = Categorie.objects.create(entreprise=self.entreprise_a, nom="Cat")
        self.produit = Produit.objects.create(
            entreprise=self.entreprise_a, categorie=self.categorie, libelle="Produit E",
            quantite=10, prixAchat=100, prixEnGros=150, prixDetail=200,
        )

    def _payload(self, user_id):
        return {
            "id_local": "sync-1", "user": user_id,
            "lignes": [{"produit_id": self.produit.id, "quantite": 1, "prix": 200}],
            "montant": 200, "remise": 0, "date": "2026-08-17",
            "typeVente": "detail", "typePayement": "Espece",
        }

    def test_sync_ventes_refuse_dattribuer_la_vente_a_un_utilisateur_dune_autre_entreprise(self):
        self.client.login(username="vendeur_e", password="secret123")
        response = self.client.post(
            reverse("sync_ventes"), data=json.dumps(self._payload(self.vendeur_b.id)), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

        from .models import Commande
        self.assertFalse(Commande.objects.filter(client_uid="sync-1").exists())

    def test_sync_ventes_fonctionne_pour_un_utilisateur_de_la_meme_entreprise(self):
        self.client.login(username="vendeur_e", password="secret123")
        response = self.client.post(
            reverse("sync_ventes"), data=json.dumps(self._payload(self.vendeur_a.id)), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        from .models import Commande
        commande = Commande.objects.get(client_uid="sync-1")
        self.assertEqual(commande.user, self.vendeur_a)
        self.assertEqual(commande.entreprise, self.entreprise_a)
