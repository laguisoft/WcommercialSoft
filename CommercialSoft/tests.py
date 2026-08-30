from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

import os
from datetime import date

from .export_entreprise import (
    MODELES_EXPORTES,
    UTILISATEUR_MODEL_LABEL,
    compter_objets,
    construire_export,
    construire_exports_mensuels,
    taille_octets,
)
from .models import Categorie, Client, Commande, CommandeProduit, Produit, Societe


class ExportEntrepriseTests(TestCase):
    def setUp(self):
        self.categorie = Categorie.objects.create(nom="Boissons")
        self.produit = Produit.objects.create(
            categorie=self.categorie,
            libelle="Coca 33cl",
            quantite=10,
            prixAchat=100,
            prixEnGros=150,
            prixDetail=200,
            quantiteTotal=10,
        )
        self.societe = Societe.objects.create(nom="ACME", telephone="000")
        self.client_obj = Client.objects.create(
            societe=self.societe,
            nom="Jean Client",
            pourcentage=0,
            detteMaximale=0,
        )
        User = get_user_model()
        self.user = User.objects.create_user(username="vendeur1", password="secret123")

    def test_construire_export_contient_tous_les_objets(self):
        paquet = construire_export()

        self.assertEqual(paquet["format_version"], 1)
        self.assertIn("empreinte_sha256", paquet)
        self.assertEqual(paquet["compteurs"]["commercialsoft.produit"], 1)
        self.assertEqual(paquet["compteurs"]["commercialsoft.client"], 1)
        self.assertEqual(paquet["compteurs"][UTILISATEUR_MODEL_LABEL], 1)

        # Chaque modele declare est bien present dans le manifeste
        for label in MODELES_EXPORTES:
            self.assertIn(label.lower(), paquet["compteurs"])

        # Le mot de passe ne doit jamais apparaitre dans l'export
        contenu_utilisateur = next(
            o for o in paquet["objets"] if o["model"] == UTILISATEUR_MODEL_LABEL
        )
        self.assertNotIn("password", contenu_utilisateur["fields"])
        self.assertEqual(contenu_utilisateur["fields"]["username"], "vendeur1")

    def test_compter_objets_correspond_a_construire_export(self):
        self.assertEqual(compter_objets(), construire_export()["compteurs"])

    def test_vue_export_reservee_au_superadmin(self):
        User = get_user_model()
        User.objects.create_user(username="gerant", password="secret123", is_staff=True)
        self.client.login(username="gerant", password="secret123")

        response = self.client.get(reverse("exportEntreprise"))
        self.assertEqual(response.status_code, 403)

    def test_vue_export_telecharge_le_json_pour_superadmin(self):
        User = get_user_model()
        User.objects.create_superuser(username="admin", password="secret123")
        self.client.login(username="admin", password="secret123")

        response = self.client.post(reverse("exportEntreprise"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment;", response["Content-Disposition"])


class ExportEntrepriseDecoupageMensuelTests(TestCase):
    """export_entreprise bascule automatiquement sur plusieurs fichiers
    mensuels quand l'export complet depasse le seuil de taille, pour eviter
    une erreur '413 Request Entity Too Large' a l'upload dans Saas."""

    def setUp(self):
        self.categorie = Categorie.objects.create(nom="Boissons")
        self.produits = [
            Produit.objects.create(
                categorie=self.categorie, libelle=f"Produit{i}", quantite=100,
                prixAchat=100, prixEnGros=150, prixDetail=200, quantiteTotal=100,
            )
            for i in range(3)
        ]
        self.client_obj = Client.objects.create(nom="Client Test", pourcentage=0, detteMaximale=0)
        User = get_user_model()
        self.user = User.objects.create_user(username="vendeur1", password="secret123")

        # Des ventes reparties sur 3 mois distincts
        for mois in (1, 2, 3):
            for jour in range(1, 4):
                d = date(2025, mois, jour)
                commande = Commande.objects.create(
                    user=self.user, client=self.client_obj, montant=1000, montantAchat=500,
                    date=d, typeVente="detail", typePayement="Espece",
                )
                CommandeProduit.objects.create(
                    commande=commande, produit=self.produits[jour % 3], quantite=1, prix=1000, date=d,
                )

    def test_taille_octets_reflete_le_contenu_reel(self):
        paquet = construire_export()
        self.assertGreater(taille_octets(paquet), 0)

    def test_construire_exports_mensuels_couvre_toutes_les_commandes_sans_doublon(self):
        paquets = construire_exports_mensuels()

        self.assertEqual(len(paquets), 3)
        empreintes = {p["empreinte_sha256"] for p in paquets}
        self.assertEqual(len(empreintes), 3, "chaque lot doit avoir une empreinte distincte")

        total_commandes = sum(p["compteurs"]["commercialsoft.commande"] for p in paquets)
        self.assertEqual(total_commandes, 9)

        # Les donnees de reference (produits, client) sont repetees a l'identique dans chaque lot
        for p in paquets:
            self.assertEqual(p["compteurs"]["commercialsoft.produit"], 3)
            self.assertEqual(p["compteurs"]["commercialsoft.client"], 1)
            self.assertEqual(p["lot"]["total"], 3)

        # Une commande et sa ligne de produit restent toujours dans le meme lot
        for p in paquets:
            self.assertEqual(
                p["compteurs"]["commercialsoft.commande"],
                p["compteurs"]["commercialsoft.commandeproduit"],
            )

    def test_export_entreprise_bascule_automatiquement_sous_seuil_bas(self):
        from io import StringIO
        from django.core.management import call_command
        import tempfile

        with tempfile.TemporaryDirectory() as dossier:
            sortie = StringIO()
            call_command("export_entreprise", "--seuil-mo", "0.001", "--dossier", dossier, stdout=sortie)

            fichiers = sorted(os.listdir(dossier))
            self.assertEqual(len(fichiers), 3)
            self.assertIn("decoupage automatique", sortie.getvalue())

    def test_export_entreprise_reste_un_seul_fichier_sous_le_seuil(self):
        from io import StringIO
        from django.core.management import call_command
        import tempfile

        with tempfile.TemporaryDirectory() as dossier:
            sortie = StringIO()
            chemin_sortie = os.path.join(dossier, "complet.json")
            call_command("export_entreprise", "--output", chemin_sortie, stdout=sortie)

            self.assertTrue(os.path.exists(chemin_sortie))
            self.assertEqual(os.listdir(dossier), ["complet.json"])


class SynchronisationHorsLigneGlobaleTests(TestCase):
    """La synchronisation (ventes + réceptions) doit démarrer dès qu'une
    page s'affiche après connexion, pas seulement quand l'utilisateur ouvre
    la page de vente ou de réception. offline-core.js doit donc être chargé
    sur toute page qui étend starter-page.html, y compris celles qui
    redéfinissent le bloc js (ex. reception2.html)."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="gerant_sync", password="secret123")
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

