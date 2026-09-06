import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from . import import_entreprise as import_entreprise_module
from . import reparer_import_client_portail as reparation_module
from .models import (
    Categorie, Client, ClientSpecial, Commande, CommandeProduit, Fournisseur,
    ImportJournal, Livraison, Produit,
)
from .views import utilisateur_de_entreprise, utilisateurs_de_entreprise
from tenants.models import Entreprise


def _paquet_export_exemple():
    """Construit un paquet minimal au format produit par export_entreprise (branche main),
    couvrant categorie/produit special/client/clientspecial/commande/utilisateur."""
    return {
        'format_version': 1,
        'exporte_le': '2026-08-01T00:00:00+00:00',
        'empreinte_sha256': 'abc123',
        'compteurs': {},
        'objets': [
            {'model': 'accounts.customuser', 'pk': 1, 'fields': {
                'username': 'ancien_vendeur', 'first_name': 'Amara', 'last_name': 'Kaba',
                'is_active': True, 'groupes': ['Administrateur'],
            }},
            {'model': 'commercialsoft.categorie', 'pk': 10, 'fields': {'nom': 'Medicaments'}},
            {'model': 'commercialsoft.produit', 'pk': 20, 'fields': {
                'codebare': None, 'categorie': 10, 'libelle': 'Paracetamol', 'quantite': 100,
                'prixAchat': '500', 'prixEnGros': '700', 'prixDetail': '1000', 'autrePrix': '0',
                'date': '2026-01-01', 'datePeremption': '2027-01-01', 'seuil': 5,
                'commentaire': None, 'quantiteTotal': 100, 'special': True,
            }},
            {'model': 'commercialsoft.client', 'pk': 30, 'fields': {
                'societe': None, 'nom': 'Client Ancien', 'telephone': '620000001', 'adresse': None,
                'email': None, 'matricule': None, 'pourcentage': 0, 'detteMaximale': 0, 'user': None,
            }},
            {'model': 'commercialsoft.clientspecial', 'pk': 40, 'fields': {
                'nom': 'Diallo', 'prenom': 'Fatou', 'telephone': '620000002',
            }},
            {'model': 'commercialsoft.commande', 'pk': 50, 'fields': {
                'user': 1, 'client': 30, 'clientSpecial': 40, 'montant': 2000, 'remise': 0,
                'date': '2026-01-15T10:00:00+00:00', 'typeVente': 'detail', 'typePayement': 'Espece',
                'montantAchat': 1000, 'client_uid': 'uid-ancien-50',
            }},
            {'model': 'commercialsoft.commandeproduit', 'pk': 60, 'fields': {
                'produit': 20, 'commande': 50, 'quantite': 2, 'date': '2026-01-15', 'prix': 1000,
            }},
        ],
    }


class ProduitsSpeciauxTests(TestCase):
    """Verifie le fonctionnement de ClientSpecial et son etancheite entre tenants."""


class UtilisateurDeEntrepriseTests(TestCase):
    """CustomUser n'est pas un TenantScopedModel (login partage par tout le
    Saas) : ces helpers doivent etre le seul point de resolution d'un
    utilisateur a partir d'un id fourni par le client, pour ne jamais
    exposer/filtrer par un compte d'une autre entreprise."""


    def setUp(self):
        User = get_user_model()
        self.entreprise_a = Entreprise.objects.create(nom="Boutique A", ville="Conakry")
        self.entreprise_b = Entreprise.objects.create(nom="Boutique B", ville="Kankan")

        self.user_a = User.objects.create_user(username="vendeur_a", password="secret123", entreprise=self.entreprise_a)
        self.user_b = User.objects.create_user(username="vendeur_b", password="secret123", entreprise=self.entreprise_b)
        permission_vente = Permission.objects.get(codename="view_commande")
        self.user_a.user_permissions.add(permission_vente)
        self.user_b.user_permissions.add(permission_vente)

        self.categorie_a = Categorie.objects.create(entreprise=self.entreprise_a, nom="Medicaments")
        self.produit_special_a = Produit.objects.create(
            entreprise=self.entreprise_a,
            categorie=self.categorie_a,
            libelle="Antibiotique",
            quantite=50,
            prixAchat=1000,
            prixEnGros=1500,
            prixDetail=2000,
            special=True,
        )

    def test_sync_ventes_cree_le_client_special_scope_a_lentreprise(self):
        self.client.login(username="vendeur_a", password="secret123")
        payload = {
            "id_local": "abc123",
            "user": self.user_a.id,
            "lignes": [{"produit_id": self.produit_special_a.id, "quantite": 2, "prix": 2000}],
            "montant": 4000,
            "remise": 0,
            "date": "2026-08-17",
            "typeVente": "detail",
            "typePayement": "Espece",
            "clientSpecialNom": "Diallo",
            "clientSpecialPrenom": "Aminata",
            "clientSpecialTelephone": "622334455",
        }
        response = self.client.post(
            reverse("sync_ventes"), data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.assertEqual(ClientSpecial.objects.count(), 1)
        client_special = ClientSpecial.objects.get()
        self.assertEqual(client_special.entreprise, self.entreprise_a)
        self.assertEqual(client_special.telephone, "622334455")

        commande = Commande.objects.get(client_uid="abc123")
        self.assertEqual(commande.clientSpecial, client_special)
        self.assertEqual(commande.entreprise, self.entreprise_a)

    def test_client_special_dune_entreprise_invisible_pour_une_autre(self):
        ClientSpecial.objects.create(entreprise=self.entreprise_a, nom="Diallo", telephone="622334455")

        self.client.login(username="vendeur_b", password="secret123")
        response = self.client.post(reverse("rechercheClientSpecial"), data={"recherche": "Diallo"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["clients"], [])

    def test_recherche_client_special_globale_ne_remonte_que_lentreprise_courante(self):
        commande = Commande.objects.create(
            entreprise=self.entreprise_a,
            user=self.user_a,
            montant=2000,
            montantAchat=1000,
        )
        CommandeProduit.objects.create(
            entreprise=self.entreprise_a,
            commande=commande,
            produit=self.produit_special_a,
            quantite=1,
            prix=2000,
        )

        self.client.login(username="vendeur_b", password="secret123")
        response = self.client.post(reverse("rechercheClientSpecial"), data={"recherche": ""})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["global"])
        self.assertEqual(data["achats"], [])


class ModifierCommandeTests(TestCase):
    @staticmethod
    def _permissions_commande():
        return Permission.objects.filter(codename__in=["change_commande", "view_commande"])

    def setUp(self):
        User = get_user_model()
        self.entreprise = Entreprise.objects.create(nom="Boutique C", ville="Nzerekore")
        groupe_admin, _ = Group.objects.get_or_create(name="Administrateur")
        self.user = User.objects.create_user(username="gerant_c", password="secret123", entreprise=self.entreprise)
        self.user.groups.add(groupe_admin)
        self.user.user_permissions.add(*self._permissions_commande())
        self.client.login(username="gerant_c", password="secret123")

        self.produit = Produit.objects.create(
            entreprise=self.entreprise,
            libelle="Riz 25kg",
            quantite=20,
            prixAchat=100000,
            prixEnGros=110000,
            prixDetail=120000,
        )
        self.commande = Commande.objects.create(
            entreprise=self.entreprise,
            user=self.user,
            montant=120000,
            montantAchat=100000,
        )
        CommandeProduit.objects.create(
            entreprise=self.entreprise,
            commande=self.commande,
            produit=self.produit,
            quantite=1,
            prix=120000,
        )
        self.produit.quantite = 19
        self.produit.save()

    def test_page_modification_commande_s_affiche(self):
        response = self.client.get(reverse("commerce_modVente", args=[self.commande.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modifier la commande")

    def test_page_client_special_s_affiche(self):
        response = self.client.get(reverse("commerce_clientSpecial"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historique client produit special")

    def test_modification_reajuste_le_stock(self):
        response = self.client.post(
            reverse("commerce_modVente", args=[self.commande.id]),
            data={
                "jsonDataInput": json.dumps([
                    {"produit_id": self.produit.id, "quantite": 3, "prix": 120000},
                ]),
                "date": "2026-08-17",
                "typeVente": "detail",
                "typePayement": "Espece",
                "remise": "0",
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["success"])

        self.produit.refresh_from_db()
        # stock initial 20, -1 (vente d'origine) puis reajuste +1 -3 (nouvelle vente) = 17
        self.assertEqual(self.produit.quantite, 17)

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant, 360000)


class ImportEntrepriseModuleTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique D", ville="Labe")
        self.autre_entreprise = Entreprise.objects.create(nom="Boutique E", ville="Mamou")
        User = get_user_model()
        self.superadmin = User.objects.create_superuser(username="root", password="secret123")

    def test_analyser_signale_le_produit_deja_present(self):
        Produit.objects.create(
            entreprise=self.entreprise, libelle="Paracetamol", quantite=1,
            prixAchat=1, prixEnGros=1, prixDetail=1,
        )
        rapport = import_entreprise_module.analyser(_paquet_export_exemple(), self.entreprise)
        self.assertTrue(any("Paracetamol" in c for c in rapport['conflits']))
        self.assertEqual(rapport['utilisateurs'][0]['username'], 'ancien_vendeur')

    def test_executer_cree_et_scope_toutes_les_donnees(self):
        paquet = _paquet_export_exemple()
        mapping = {1: {'action': 'creer'}}
        rapport = import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)

        self.assertEqual(rapport['crees']['commercialsoft.produit'], 1)
        self.assertEqual(rapport['crees']['commercialsoft.commande'], 1)
        self.assertIn('ancien_vendeur', rapport['comptes_crees'])

        produit = Produit.objects.get(libelle="Paracetamol")
        self.assertEqual(produit.entreprise, self.entreprise)
        self.assertTrue(produit.special)

        client_special = ClientSpecial.objects.get(telephone="620000002")
        self.assertEqual(client_special.entreprise, self.entreprise)

        commande = Commande.objects.get(client_uid="uid-ancien-50")
        self.assertEqual(commande.entreprise, self.entreprise)
        self.assertEqual(commande.clientSpecial, client_special)
        self.assertEqual(commande.user.username, "ancien_vendeur")

        self.assertTrue(ImportJournal.objects.filter(entreprise=self.entreprise, empreinte_sha256="abc123").exists())

    def test_executer_refuse_le_double_import(self):
        paquet = _paquet_export_exemple()
        mapping = {1: {'action': 'creer'}}
        import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)

        with self.assertRaises(ValueError):
            import_entreprise_module.executer(paquet, self.entreprise, {1: {'action': 'creer'}}, self.superadmin)

    def test_import_ne_fuite_pas_vers_une_autre_entreprise(self):
        paquet = _paquet_export_exemple()
        import_entreprise_module.executer(paquet, self.entreprise, {1: {'action': 'creer'}}, self.superadmin)

        self.assertFalse(Produit.objects.filter(entreprise=self.autre_entreprise, libelle="Paracetamol").exists())
        self.assertFalse(Client.objects.filter(entreprise=self.autre_entreprise, nom="Client Ancien").exists())
        self.assertFalse(ClientSpecial.objects.filter(entreprise=self.autre_entreprise).exists())

    def test_lier_a_un_utilisateur_saas_existant_ne_cree_pas_de_compte(self):
        User = get_user_model()
        vendeur_existant = User.objects.create_user(username="vendeur_existant", password="x", entreprise=self.entreprise)
        paquet = _paquet_export_exemple()
        rapport = import_entreprise_module.executer(
            paquet, self.entreprise, {1: {'action': 'lier', 'user_id': vendeur_existant.id}}, self.superadmin,
        )
        self.assertEqual(rapport['comptes_crees'], [])
        commande = Commande.objects.get(client_uid="uid-ancien-50")
        self.assertEqual(commande.user, vendeur_existant)

    def _paquet_avec_client_portail(self, empreinte, nom_client="Client Avec Compte"):
        return {
            'format_version': 1,
            'exporte_le': '2026-08-01T00:00:00+00:00',
            'empreinte_sha256': empreinte,
            'compteurs': {},
            'objets': [
                {'model': 'accounts.customuser', 'pk': 1, 'fields': {
                    'username': 'ancien_vendeur', 'first_name': '', 'last_name': '',
                    'is_active': True, 'groupes': ['Administrateur'],
                }},
                {'model': 'accounts.customuser', 'pk': 2, 'fields': {
                    'username': 'ancien_client_portail', 'first_name': '', 'last_name': '',
                    'is_active': True, 'groupes': ['Client Boutique'],
                }},
                {'model': 'commercialsoft.client', 'pk': 30, 'fields': {
                    'societe': None, 'nom': nom_client, 'telephone': '620000001', 'adresse': None,
                    'email': None, 'matricule': None, 'pourcentage': 0, 'detteMaximale': 0, 'user': 2,
                }},
            ],
        }

    def test_executer_relie_le_compte_portail_dun_client_cree(self):
        """Le compte portail (Client.user, cote main) doit etre restaure a
        l'import, sinon hasattr(user, 'client_profile') devient faux et le
        client se retrouve route vers le tableau de bord staff au login."""
        paquet = self._paquet_avec_client_portail('empreinte-client-portail-1')
        mapping = {1: {'action': 'creer'}, 2: {'action': 'creer'}}
        import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)

        client = Client.objects.get(entreprise=self.entreprise, nom="Client Avec Compte")
        compte_portail = get_user_model().objects.get(username='ancien_client_portail')
        self.assertEqual(client.user_id, compte_portail.id)
        self.assertTrue(hasattr(compte_portail, 'client_profile'))
        self.assertEqual(compte_portail.client_profile, client)

    def test_executer_relie_le_compte_portail_dun_client_deja_existant_sans_lien(self):
        """Un client deja reutilise (meme nom pour l'entreprise cible) mais
        sans compte portail doit recevoir celui de l'export, sans dupliquer
        le client (principe : jamais d'ecrasement, mais pas d'orphelin non plus)."""
        Client.objects.create(
            entreprise=self.entreprise, nom="Client Avec Compte",
            pourcentage=0, detteMaximale=0,
        )
        paquet = self._paquet_avec_client_portail('empreinte-client-portail-2')
        mapping = {1: {'action': 'creer'}, 2: {'action': 'creer'}}
        rapport = import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)

        self.assertEqual(rapport['reutilises'].get('commercialsoft.client'), 1)
        client = Client.objects.get(entreprise=self.entreprise, nom="Client Avec Compte")
        compte_portail = get_user_model().objects.get(username='ancien_client_portail')
        self.assertEqual(client.user_id, compte_portail.id)

    def test_executer_ne_pas_ecraser_un_compte_portail_deja_lie(self):
        """Un client reutilise qui a deja son propre compte portail cote Saas
        ne doit jamais se faire reassigner celui de l'export."""
        User = get_user_model()
        compte_saas_existant = User.objects.create_user(
            username="compte_saas_deja_la", password="x", entreprise=self.entreprise,
        )
        client_existant = Client.objects.create(
            entreprise=self.entreprise, nom="Client Avec Compte",
            pourcentage=0, detteMaximale=0, user=compte_saas_existant,
        )
        paquet = self._paquet_avec_client_portail('empreinte-client-portail-3')
        mapping = {1: {'action': 'creer'}, 2: {'action': 'creer'}}
        import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)

        client_existant.refresh_from_db()
        self.assertEqual(client_existant.user_id, compte_saas_existant.id)


class ReparationImportClientPortailTests(TestCase):
    """Outil de reparation pour les Client importes AVANT le correctif du
    lien vers leur compte portail (import_entreprise.executer) : rejoue le
    meme fichier d'export deja utilise, sans repasser par un nouvel import
    (bloque par le controle 'deja importe')."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique G", ville="Kindia")
        User = get_user_model()
        self.superadmin = User.objects.create_superuser(username="root3", password="secret123")

    def _paquet(self, empreinte, nom_client="Client Avec Compte"):
        return {
            'format_version': 1,
            'exporte_le': '2026-08-01T00:00:00+00:00',
            'empreinte_sha256': empreinte,
            'compteurs': {},
            'objets': [
                {'model': 'accounts.customuser', 'pk': 1, 'fields': {
                    'username': 'ancien_vendeur', 'first_name': '', 'last_name': '',
                    'is_active': True, 'groupes': ['Administrateur'],
                }},
                {'model': 'accounts.customuser', 'pk': 2, 'fields': {
                    'username': 'ancien_client_portail', 'first_name': '', 'last_name': '',
                    'is_active': True, 'groupes': ['Client Boutique'],
                }},
                {'model': 'commercialsoft.client', 'pk': 30, 'fields': {
                    'societe': None, 'nom': nom_client, 'telephone': '620000001', 'adresse': None,
                    'email': None, 'matricule': None, 'pourcentage': 0, 'detteMaximale': 0, 'user': 2,
                }},
            ],
        }

    def _importer_sans_lien(self, paquet):
        """Simule un import fait avant le correctif : le Client se retrouve
        sans compte portail, mais le compte Saas existe deja (cas --creer)."""
        mapping = {1: {'action': 'creer'}, 2: {'action': 'creer'}}
        import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)
        Client.objects.filter(entreprise=self.entreprise, nom="Client Avec Compte").update(user=None)

    def test_analyser_resout_automatiquement_le_meme_nom_dutilisateur(self):
        paquet = self._paquet('empreinte-reparation-1')
        self._importer_sans_lien(paquet)

        rapport = reparation_module.analyser_reparation(paquet, self.entreprise)
        self.assertEqual(rapport['resolus'], [{
            'client': 'Client Avec Compte', 'username': 'ancien_client_portail',
            'user_id': get_user_model().objects.get(username='ancien_client_portail').id,
        }])
        self.assertEqual(rapport['deja_lies'], [])
        self.assertEqual(rapport['ambigus'], [])

    def test_executer_reparation_relie_automatiquement(self):
        paquet = self._paquet('empreinte-reparation-2')
        self._importer_sans_lien(paquet)

        rapport = reparation_module.executer_reparation(paquet, self.entreprise)
        self.assertEqual(rapport['lies'], ['Client Avec Compte'])

        client = Client.objects.get(entreprise=self.entreprise, nom="Client Avec Compte")
        compte_portail = get_user_model().objects.get(username='ancien_client_portail')
        self.assertEqual(client.user_id, compte_portail.id)

    def test_executer_reparation_ne_touche_pas_un_client_deja_relie(self):
        paquet = self._paquet('empreinte-reparation-3')
        self._importer_sans_lien(paquet)
        client = Client.objects.get(entreprise=self.entreprise, nom="Client Avec Compte")
        autre_compte = get_user_model().objects.create_user(
            username="deja_correct", password="x", entreprise=self.entreprise,
        )
        client.user = autre_compte
        client.save(update_fields=['user'])

        rapport = reparation_module.executer_reparation(paquet, self.entreprise)
        self.assertEqual(rapport['lies'], [])

        client.refresh_from_db()
        self.assertEqual(client.user_id, autre_compte.id)

    def test_executer_reparation_avec_lier_explicite_pour_un_cas_ambigu(self):
        paquet = self._paquet('empreinte-reparation-4')
        # Le compte Saas n'a pas garde le meme username (ex : relie via --lier
        # a un compte deja existant lors de l'import d'origine).
        mapping = {1: {'action': 'creer'}, 2: {'action': 'creer'}}
        import_entreprise_module.executer(paquet, self.entreprise, mapping, self.superadmin)
        client = Client.objects.get(entreprise=self.entreprise, nom="Client Avec Compte")
        compte_reel = client.user
        compte_reel.username = "nom_different_du_username_saas"
        compte_reel.save(update_fields=['username'])
        client.user = None
        client.save(update_fields=['user'])

        rapport_analyse = reparation_module.analyser_reparation(paquet, self.entreprise)
        self.assertEqual(rapport_analyse['ambigus'], [{
            'client': 'Client Avec Compte', 'ancien_username': 'ancien_client_portail',
        }])

        rapport = reparation_module.executer_reparation(
            paquet, self.entreprise, overrides={'Client Avec Compte': 'nom_different_du_username_saas'},
        )
        self.assertEqual(rapport['lies'], ['Client Avec Compte'])
        client.refresh_from_db()
        self.assertEqual(client.user_id, compte_reel.id)


class ImportEntrepriseViewTests(TestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique F", ville="Boke")
        User = get_user_model()
        self.superadmin = User.objects.create_superuser(username="root2", password="secret123")
        self.gerant = User.objects.create_user(username="gerant_f", password="secret123", entreprise=self.entreprise)

    def _fichier_export(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        contenu = json.dumps(_paquet_export_exemple()).encode('utf-8')
        return SimpleUploadedFile("export.json", contenu, content_type="application/json")

    def test_reservee_au_superadmin(self):
        self.client.login(username="gerant_f", password="secret123")
        response = self.client.get(reverse("importEntreprise"))
        self.assertEqual(response.status_code, 403)

    def test_import_correct_meme_si_le_superadmin_navigue_une_autre_entreprise(self):
        """Le superadmin a 'Boutique F' comme entreprise courante en session
        (choisie sur une autre page) mais importe vers une AUTRE entreprise :
        le filtrage automatique par entreprise courante ne doit jamais se
        combiner avec les filtres explicites du moteur d'import (sinon les
        verifications de doublon renverraient toujours "rien trouve" et
        dupliqueraient les donnees a chaque import)."""
        autre_entreprise = Entreprise.objects.create(nom="Boutique G", ville="Kindia")
        Produit.objects.create(
            entreprise=autre_entreprise, libelle="Paracetamol", quantite=1,
            prixAchat=1, prixEnGros=1, prixDetail=1,
        )

        self.client.login(username="root2", password="secret123")
        # Le superadmin choisit "Boutique F" comme entreprise courante (session)
        self.client.post(reverse('choisir_entreprise'), data={'entreprise_id': self.entreprise.id})

        etape1 = self.client.post(reverse("importEntreprise"), data={
            'etape': '1', 'fichier': self._fichier_export(), 'entreprise_id': autre_entreprise.id,
        })
        self.assertEqual(etape1.status_code, 200)
        rapport = etape1.context['rapport']
        self.assertTrue(any("Paracetamol" in c for c in rapport['conflits']))

        etape2 = self.client.post(reverse("importEntreprise"), data={
            'etape': '2', 'token': etape1.context['token'], 'entreprise_id': autre_entreprise.id,
            'mapping_1': 'creer',
        })
        self.assertEqual(etape2.status_code, 200)

        # Le produit deja existant pour "Boutique G" doit avoir ete reutilise,
        # jamais duplique
        self.assertEqual(Produit.objects.filter(entreprise=autre_entreprise, libelle="Paracetamol").count(), 1)

    def test_parcours_complet_upload_puis_confirmation(self):
        self.client.login(username="root2", password="secret123")

        etape1 = self.client.post(reverse("importEntreprise"), data={
            'etape': '1', 'fichier': self._fichier_export(), 'entreprise_id': self.entreprise.id,
        })
        self.assertEqual(etape1.status_code, 200)
        self.assertContains(etape1, "ancien_vendeur")
        token = etape1.context['token']

        etape2 = self.client.post(reverse("importEntreprise"), data={
            'etape': '2', 'token': token, 'entreprise_id': self.entreprise.id,
            'mapping_1': 'creer',
        })
        self.assertEqual(etape2.status_code, 200)
        self.assertContains(etape2, "Import terminé")

        self.assertTrue(Produit.objects.filter(entreprise=self.entreprise, libelle="Paracetamol").exists())
        self.assertTrue(ImportJournal.objects.filter(entreprise=self.entreprise).exists())


class ResolutionUtilisateurDeEntrepriseTests(TestCase):
    """utilisateur(s)_de_entreprise est le seul point de resolution d'un
    agent pour les listes deroulantes/filtres "Utilisateur" des pages de
    recherche et statistiques : ne doit jamais exposer un utilisateur d'une
    autre entreprise, ni un compte portail client (cree uniquement pour
    qu'un client passe commande a distance, ce n'est pas un agent)."""

    def setUp(self):
        self.entreprise_a = Entreprise.objects.create(nom="Boutique H", ville="Faranah")
        self.entreprise_b = Entreprise.objects.create(nom="Boutique I", ville="Gueckedou")
        User = get_user_model()
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

    def test_utilisateurs_de_entreprise_exclut_les_comptes_portail_client(self):
        compte_portail = get_user_model().objects.create_user(
            username="client_portail_a", password="x", entreprise=self.entreprise_a,
        )
        Client.objects.create(
            entreprise=self.entreprise_a, nom="Client Avec Compte Portail",
            pourcentage=0, detteMaximale=0, user=compte_portail,
        )
        request = type('R', (), {'entreprise': self.entreprise_a})()
        noms = set(utilisateurs_de_entreprise(request).values_list('username', flat=True))
        self.assertIn('vendeur_a', noms)
        self.assertNotIn('client_portail_a', noms)

    def test_utilisateur_de_entreprise_refuse_un_compte_portail_client(self):
        compte_portail = get_user_model().objects.create_user(
            username="client_portail_b", password="x", entreprise=self.entreprise_a,
        )
        Client.objects.create(
            entreprise=self.entreprise_a, nom="Client Avec Compte Portail 2",
            pourcentage=0, detteMaximale=0, user=compte_portail,
        )
        request = type('R', (), {'entreprise': self.entreprise_a})()
        self.assertIsNone(utilisateur_de_entreprise(request, compte_portail.id))


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


class SyncLivraisonsOfflineTests(TestCase):
    """api_sync_livraisons doit etre idempotent comme sync_ventes (cf. id_local/
    client_uid) : un rejeu du meme id_local (timeout cote offline-core.js alors
    que le premier envoi avait en realite reussi cote serveur) ne doit ni
    recreer la livraison, ni redoubler l'entree de stock du produit."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        User = get_user_model()
        self.user = User.objects.create_user(
            username="gestionnaire", password="secret123", entreprise=self.entreprise
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_livraison", "add_livraisonproduit"]
        ))
        self.client.login(username="gestionnaire", password="secret123")

        self.fournisseur = Fournisseur.objects.create(
            entreprise=self.entreprise, nom="Fournisseur Test", adresse="Conakry", telephone="620000000"
        )
        self.categorie = Categorie.objects.create(entreprise=self.entreprise, nom="Divers")
        self.produit = Produit.objects.create(
            entreprise=self.entreprise, categorie=self.categorie, libelle="Riz",
            quantite=10, quantiteTotal=10, prixAchat=1000, prixEnGros=1200, prixDetail=1500,
        )

    def _payload(self):
        return {
            "id_local": "liv-local-1",
            "fournisseur": self.fournisseur.id,
            "lignes": [{
                "produit_id": self.produit.id, "quantite": 5, "prix": 1100,
                "prixEnGros": 1300, "prixDetail": 1600,
            }],
            "montant": 5500,
            "date": "2026-08-17",
            "typePayement": "Espece",
        }

    def test_sync_cree_la_livraison_et_met_a_jour_le_stock(self):
        response = self.client.post(
            reverse("api_sync_livraisons"), data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Livraison.objects.filter(client_uid="liv-local-1").count(), 1)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite, 15)
        self.assertEqual(self.produit.quantiteTotal, 15)

    def test_rejouer_le_meme_id_local_ne_double_pas_le_stock(self):
        payload = self._payload()
        for _ in range(2):
            response = self.client.post(
                reverse("api_sync_livraisons"), data=json.dumps(payload), content_type="application/json",
            )
            self.assertEqual(response.status_code, 200, response.content)

        self.assertEqual(Livraison.objects.filter(client_uid="liv-local-1").count(), 1)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite, 15)
        self.assertEqual(self.produit.quantiteTotal, 15)


class AccesReceptionGestionnaireTests(TestCase):
    """@user_passes_test(est_administrateur, est_gestionnaire) etait invalide :
    le 2e argument positionnel de user_passes_test est login_url, pas un second
    test - ca ne faisait donc passer que les Administrateur, et un Gestionnaire
    refuse declenchait un NoReverseMatch nonsense (resolve_url(est_gestionnaire))
    au lieu d'un redirect propre, soit une erreur 500 en pratique. Un
    utilisateur du groupe Gestionnaire (role courant pour la reception au
    quotidien) doit pouvoir acceder aux pages de reception."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        User = get_user_model()
        self.gestionnaire = User.objects.create_user(
            username="gestionnaire", password="secret123", entreprise=self.entreprise
        )
        groupe_gestionnaire, _ = Group.objects.get_or_create(name="Gestionnaire")
        self.gestionnaire.groups.add(groupe_gestionnaire)
        self.gestionnaire.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_livraison", "add_livraisonproduit"]
        ))
        self.client.login(username="gestionnaire", password="secret123")

    def test_page_reception_accessible_a_un_gestionnaire(self):
        response = self.client.get(reverse("commerce_reception"))
        self.assertEqual(response.status_code, 200)

    def test_api_reception_accessible_a_un_gestionnaire(self):
        response = self.client.get(reverse("api_reception"))
        self.assertEqual(response.status_code, 200)


class SyncLivraisonsLigneInvalideTests(TestCase):
    """Reproduit le bug signale : une ligne avec un prix d'achat a 0 (autorise
    a tort cote JS par `pa < 0` au lieu de `pa <= 0`) etait silencieusement
    ignoree par api_sync_livraisons (`prix <= 0: continue`), tout en renvoyant
    success=True car la Livraison (entete facture) etait quand meme creee :
    la facture apparaissait "enregistree" sans que le stock du produit ne
    bouge. Le serveur doit desormais refuser une livraison dont aucune ligne
    n'a pu etre traitee, plutot que de repondre un faux succes."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(nom="Boutique Test", ville="Conakry")
        User = get_user_model()
        self.user = User.objects.create_user(
            username="gestionnaire", password="secret123", entreprise=self.entreprise
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=["add_livraison", "add_livraisonproduit"]
        ))
        self.client.login(username="gestionnaire", password="secret123")

        self.fournisseur = Fournisseur.objects.create(
            entreprise=self.entreprise, nom="Fournisseur Test", adresse="Conakry", telephone="620000000"
        )
        self.categorie = Categorie.objects.create(entreprise=self.entreprise, nom="Divers")
        self.produit = Produit.objects.create(
            entreprise=self.entreprise, categorie=self.categorie, libelle="Riz",
            quantite=10, quantiteTotal=10, prixAchat=1000, prixEnGros=1200, prixDetail=1500,
        )

    def test_prix_a_zero_est_refuse_sans_toucher_au_stock(self):
        payload = {
            "id_local": "liv-prix-zero",
            "fournisseur": self.fournisseur.id,
            "lignes": [{
                "produit_id": self.produit.id, "quantite": 5, "prix": 0,
                "prixEnGros": 0, "prixDetail": 0,
            }],
            "montant": 0,
            "date": "2026-08-17",
            "typePayement": "Espece",
        }
        response = self.client.post(
            reverse("api_sync_livraisons"), data=json.dumps(payload), content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])

        # Ni la facture ni la mise a jour de stock ne doivent avoir ete
        # enregistrees (transaction annulee dans son ensemble).
        self.assertFalse(Livraison.objects.filter(client_uid="liv-prix-zero").exists())
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite, 10)
        self.assertEqual(self.produit.quantiteTotal, 10)
