"""Import ponctuel d'une ancienne base MySQL (dump mysqldump/phpMyAdmin,
schema type 'apphar' : pharmacie/grossiste avec vente a credit) vers une
entreprise du nouveau Saas.

Voir la conversation d'origine pour le detail des choix de mapping :
- Un compte utilisateur Django est cree par utilisateur historique
  (mot de passe temporaire genere, a communiquer puis a faire changer).
- Les references texte libres sans equivalent dans le nouveau modele
  (ex : commentaire de dette fournisseur) sont volontairement abandonnees.
- Les clients supprimes de l'ancienne base mais encore references par une
  vente sont recrees a partir du nom texte conserve sur la vente.
- Aucun logo n'est importe (fichier absent du dump).
"""
from datetime import date, datetime, time

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import CustomUser
from CommercialSoft.models import (
    Categorie,
    Categorie_Depense,
    Client,
    Commande,
    CommandeProduit,
    Depense,
    DetteFournisseur,
    Fournisseur,
    Livraison,
    LivraisonProduit,
    PretClient,
    Produit,
    Retour,
    Societe,
    VersementClient,
    VersementFournisseur,
)
from tenants.models import Entreprise

from ._mysqldump_parser import iter_insert_rows

ROLE_VERS_GROUPE = {
    'Super_Administrateur': 'Administrateur',
    'Administrateur': 'Administrateur',
    'Gerant stock': 'Gestionnaire',
    'Gestionnaire': 'Gestionnaire',
    'Utilisateur': 'Utilisateur',
}


def _texte(valeur):
    if valeur is None:
        return None
    valeur = str(valeur).strip()
    return valeur or None


def _tel(valeur):
    if not valeur:
        return None
    return str(valeur)


def _datetime_aware(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return timezone.make_aware(datetime.combine(d, time.min))


class Command(BaseCommand):
    help = (
        "Importe un dump mysqldump/phpMyAdmin de l'ancienne application "
        "(schema type 'apphar') vers une entreprise du Saas. Ne necessite "
        "aucun serveur MySQL supplementaire : le fichier .sql est lu et "
        "parse directement."
    )

    def add_arguments(self, parser):
        parser.add_argument('dump_path', help="Chemin du fichier .sql exporte de l'ancienne base")
        parser.add_argument(
            '--entreprise', required=True,
            help="Nom exact de l'entreprise cible (colonne 'nom' de tenants.Entreprise)",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Simule l'import et affiche le resume sans rien ecrire en base",
        )
        parser.add_argument(
            '--force', action='store_true',
            help=(
                "Autorise l'import meme si cette entreprise a deja des ventes "
                "importees (sinon la commande refuse de relancer pour eviter "
                "de dupliquer tout l'historique transactionnel)."
            ),
        )
        parser.add_argument(
            '--rename-login', action='append', default=[], metavar='ANCIEN:NOUVEAU',
            help=(
                "Remplace le login ANCIEN (tel qu'il apparait dans le dump) par "
                "NOUVEAU avant creation du compte. Repetable. Utile quand le meme "
                "login designe des personnes differentes selon l'ancienne base "
                "(ex: --rename-login=donso:SOGUI)."
            ),
        )
        parser.add_argument(
            '--partage-utilisateur', action='append', default=[], metavar='LOGIN',
            help=(
                "Si LOGIN existe deja pour une AUTRE entreprise, ne pas echouer : "
                "accorder a ce compte un acces supplementaire a l'entreprise cible "
                "(entreprises_additionnelles) au lieu de creer un nouveau compte. "
                "A utiliser uniquement quand il s'agit reellement de la meme "
                "personne. Repetable."
            ),
        )
        parser.add_argument(
            '--categorie-depense', default='Divers',
            help="Nom de la categorie de depense a utiliser pour les depenses importees (defaut: 'Divers').",
        )

    def handle(self, *args, **options):
        try:
            entreprise = Entreprise.objects.get(nom=options['entreprise'])
        except Entreprise.DoesNotExist as exc:
            raise CommandError(
                f"Aucune entreprise nommee \"{options['entreprise']}\"."
            ) from exc

        if not options['force'] and not options['dry_run'] and Commande.objects.filter(entreprise=entreprise).exists():
            raise CommandError(
                f"L'entreprise \"{entreprise.nom}\" a deja des ventes enregistrees. "
                "Un nouvel import creerait des doublons (ventes, prets, versements...). "
                "Relancez avec --force uniquement si vous etes sur de vouloir "
                "importer une seconde fois (ex : apres avoir vide la base manuellement)."
            )

        renommages = {}
        for paire in options['rename_login']:
            if ':' not in paire:
                raise CommandError(f"--rename-login attend ANCIEN:NOUVEAU, recu {paire!r}.")
            ancien, nouveau = paire.split(':', 1)
            renommages[ancien.strip()] = nouveau.strip()
        logins_partages = {l.strip() for l in options['partage_utilisateur']}

        with open(options['dump_path'], encoding='utf-8') as fichier:
            sql = fichier.read()

        def lignes(table):
            return list(iter_insert_rows(sql, table))

        dry_run = options['dry_run']
        comptes_crees = []
        avertissements = []

        with transaction.atomic():
            # ---------------------------------------------------------- Utilisateurs
            user_par_codeu = {}
            for row in lignes('utilisateur'):
                login_origine = row['LOGIN'].strip()
                login = renommages.get(login_origine, login_origine)
                user = CustomUser.objects.filter(username=login).first()
                if user is not None and user.entreprise_id not in (None, entreprise.id):
                    if login_origine in logins_partages or login in logins_partages:
                        user.entreprises_additionnelles.add(entreprise)
                        avertissements.append(
                            f"Compte existant \"{login}\" (entreprise principale : "
                            f"{user.entreprise}) : acces supplementaire accorde a "
                            f"\"{entreprise.nom}\" (mot de passe inchange)."
                        )
                        user_par_codeu[row['CODEU']] = user
                        continue
                    raise CommandError(
                        f"Le login \"{login}\" existe deja et appartient a une autre "
                        f"entreprise ({user.entreprise}). Renommez-le avec "
                        "--rename-login ou autorisez le partage avec "
                        "--partage-utilisateur avant de relancer l'import."
                    )
                if user is None:
                    mot_de_passe = get_random_string(12)
                    user = CustomUser.objects.create_user(
                        username=login,
                        password=mot_de_passe,
                        first_name=row['NOMPRENOMU'].strip(),
                        entreprise=entreprise,
                        is_active=(row['Activer'] or '').strip().lower() == 'oui',
                    )
                    groupe_nom = ROLE_VERS_GROUPE.get(row['type'].strip())
                    if groupe_nom:
                        groupe, _ = Group.objects.get_or_create(name=groupe_nom)
                        user.groups.add(groupe)
                    comptes_crees.append((login, mot_de_passe))
                elif user.entreprise_id is None:
                    user.entreprise = entreprise
                    user.save(update_fields=['entreprise'])
                    avertissements.append(
                        f"Compte existant \"{login}\" rattache a l'entreprise "
                        f"\"{entreprise.nom}\" (mot de passe inchange)."
                    )
                else:
                    avertissements.append(
                        f"Compte existant \"{login}\" deja rattache a "
                        f"\"{entreprise.nom}\" : reutilise tel quel (mot de passe inchange)."
                    )
                user_par_codeu[row['CODEU']] = user

            if not user_par_codeu:
                raise CommandError("Aucun utilisateur trouve dans le dump : import annule.")
            premier_user = user_par_codeu[min(user_par_codeu)]

            # -------------------------------------------------------------- Societe
            societe_par_numero = {}
            for row in lignes('societe'):
                societe, _ = Societe.objects.get_or_create(
                    entreprise=entreprise,
                    nom=row['NOM'].strip(),
                    defaults={'adresse': _texte(row['ADRESSE']) or '', 'telephone': ''},
                )
                societe_par_numero[row['NUMERO']] = societe

            # --------------------------------------------------------------- Client
            client_par_codecl = {}
            for row in lignes('client'):
                client, _ = Client.objects.get_or_create(
                    entreprise=entreprise,
                    nom=row['Nom'].strip(),
                    defaults=dict(
                        societe=societe_par_numero.get(row['Societe']),
                        telephone=_tel(row['Tel']),
                        adresse=_texte(row['Adresse']),
                        email=_texte(row['Email']),
                        matricule=_texte(row['matricule']),
                        pourcentage=row['Pourcentage'],
                        detteMaximale=row['detteMaximal'],
                    ),
                )
                client_par_codecl[row['CodeCl']] = client

            # ---------------------------------------------- Clients "orphelins"
            # (supprimes de l'ancienne base mais encore references par une vente ;
            # on les recree a partir du nom texte conserve sur la vente)
            ventes_src = lignes('vente')
            for row in ventes_src:
                code_cl = row['CodeCl']
                if code_cl in client_par_codecl:
                    continue
                nom = _texte(row['NomClient']) or f"Client historique #{code_cl}"
                client, cree = Client.objects.get_or_create(
                    entreprise=entreprise,
                    nom=nom,
                    defaults=dict(pourcentage=0, detteMaximale=0),
                )
                client_par_codecl[code_cl] = client
                if cree:
                    avertissements.append(
                        f"Client #{code_cl} ({nom}) absent de l'ancienne table client : "
                        "recree avec des valeurs par defaut (0% remise, 0 dette max)."
                    )

            # ---------------------------------------------------------- Fournisseur
            fournisseur_par_codefour = {}
            for row in lignes('fournisseur'):
                fournisseur, _ = Fournisseur.objects.get_or_create(
                    entreprise=entreprise,
                    nom=row['NOMFOUR'].strip(),
                    defaults=dict(
                        adresse=_texte(row['ADRFOUR']) or '',
                        telephone=_tel(row['Tel']) or '',
                    ),
                )
                fournisseur_par_codefour[row['CODEFOUR']] = fournisseur

            # ------------------------------------------------------------ Categorie
            categorie_par_codet = {}
            for row in lignes('typemed'):
                categorie, _ = Categorie.objects.get_or_create(
                    entreprise=entreprise, nom=row['NOMT'].strip(),
                )
                categorie_par_codet[row['CODET']] = categorie

            # -------------------------------------------------------------- Produit
            produit_par_codep = {}
            for row in lignes('produit'):
                produit, _ = Produit.objects.get_or_create(
                    entreprise=entreprise,
                    libelle=row['LIBP'].strip(),
                    defaults=dict(
                        codebare=row['CODEP'],
                        categorie=categorie_par_codet.get(row['CODET']),
                        quantite=row['QTEP'] or 0,
                        prixAchat=row['PRXACHAT'],
                        prixEnGros=row['PRXGP'],
                        prixDetail=row['PRXDP'],
                        date=row['DATEENGP'],
                        datePeremption=row['DATEPERP'],
                        seuil=row['Seuil'] or 0,
                        commentaire=_texte(row['OBS']),
                        quantiteTotal=row['QteTotalEntrer'],
                    ),
                )
                produit_par_codep[row['CODEP']] = produit

            # ------------------------------------------------------------ Livraison
            livraison_par_codeliv = {}
            for row in lignes('livraison'):
                fournisseur = fournisseur_par_codefour.get(row['CODEFOUR'])
                if fournisseur is None:
                    avertissements.append(
                        f"Livraison #{row['CODELIV']} ignoree : fournisseur "
                        f"#{row['CODEFOUR']} introuvable."
                    )
                    continue
                livraison = Livraison.objects.create(
                    entreprise=entreprise,
                    fournisseur=fournisseur,
                    date=row['DATELIVRAISON'],
                    montant=row['Montant'],
                    numeroFacture=_texte(row['NumFacture']),
                    typePayement='Espece',
                )
                livraison_par_codeliv[row['CODELIV']] = livraison

            # -------------------------------------------------------- LivraisonProduit
            livraison_produits = []
            for row in lignes('livrer'):
                livraison = livraison_par_codeliv.get(row['CODELIV'])
                produit = produit_par_codep.get(row['CODEP'])
                if livraison is None or produit is None:
                    avertissements.append(
                        f"Ligne de livraison #{row['NUMLIVRER']} ignoree "
                        f"(livraison ou produit introuvable)."
                    )
                    continue
                livraison_produits.append(LivraisonProduit(
                    entreprise=entreprise,
                    livraison=livraison,
                    produit=produit,
                    quantite=row['QTELIVRER'],
                    prix=row['Prix'],
                    prixEnGros=produit.prixEnGros,
                    prixDetail=produit.prixDetail,
                ))
            LivraisonProduit.objects.bulk_create(livraison_produits, batch_size=1000)

            # ----------------------------------------------------------- Commande
            commande_par_codev = {}
            for row in ventes_src:
                user = user_par_codeu.get(row['CODEU'])
                client = client_par_codecl.get(row['CodeCl'])
                if user is None:
                    avertissements.append(
                        f"Vente #{row['CODEV']} ignoree : utilisateur "
                        f"#{row['CODEU']} introuvable."
                    )
                    continue
                commande = Commande.objects.create(
                    entreprise=entreprise,
                    user=user,
                    client=client,
                    montant=row['MONTANTV'],
                    remise=row['REMISEV'] or 0,
                    date=_datetime_aware(row['DATEV']),
                    typeVente='detail' if row['TypeV'].strip().lower() == 'detail' else 'en gros',
                    typePayement=row['typePayement'].strip(),
                    montantAchat=row['MontantAchat'],
                )
                commande_par_codev[row['CODEV']] = commande

            # ------------------------------------------------------- CommandeProduit
            commande_produits = []
            for row in lignes('consommer'):
                commande = commande_par_codev.get(row['CODEV'])
                produit = produit_par_codep.get(row['CODEP'])
                if commande is None or produit is None:
                    avertissements.append(
                        f"Ligne de vente (produit {row['CODEP']!r}, vente "
                        f"#{row['CODEV']}) ignoree (vente ou produit introuvable)."
                    )
                    continue
                commande_produits.append(CommandeProduit(
                    entreprise=entreprise,
                    commande=commande,
                    produit=produit,
                    quantite=row['QTEV'],
                    date=row['DATEV'],
                    prix=row['prixVente'],
                ))
            CommandeProduit.objects.bulk_create(commande_produits, batch_size=1000)

            # ----------------------------------------------------------- PretClient
            prets = []
            for row in lignes('pret'):
                client = client_par_codecl.get(row['NUMCLI'])
                user = user_par_codeu.get(row['CODEU'])
                if client is None or user is None:
                    avertissements.append(
                        f"Pret #{row['CODEPR']} ignore (client ou utilisateur introuvable)."
                    )
                    continue
                commande = commande_par_codev.get(row['NumVente']) if row['NumVente'] else None
                prets.append(PretClient(
                    entreprise=entreprise,
                    client=client,
                    montant=row['MTNTPR'],
                    date=row['DATEPR'],
                    dateEcheance=row['DATEECH'],
                    payer=row['PAYER'].strip(),
                    commande=commande,
                    user=user,
                    commentaire=_texte(row['Commentaire']),
                ))
            PretClient.objects.bulk_create(prets, batch_size=1000)

            # ------------------------------------------------------- VersementClient
            versements_client = []
            for row in lignes('verssementsortie'):
                client = client_par_codecl.get(row['CODEClVerser'])
                user = user_par_codeu.get(row['CODEUtEnrg'])
                if client is None or user is None:
                    avertissements.append(
                        f"Versement client #{row['CODEV']} ignore "
                        "(client ou utilisateur introuvable)."
                    )
                    continue
                versements_client.append(VersementClient(
                    entreprise=entreprise,
                    client=client,
                    montant=row['MTNTVER'],
                    date=row['DATER'],
                    user=user,
                ))
            VersementClient.objects.bulk_create(versements_client, batch_size=1000)

            # ----------------------------------------------------- DetteFournisseur
            # Le numero de reference libre (COMMENTAIRE) de l'ancienne table n'a pas
            # d'equivalent dans DetteFournisseur : il est volontairement abandonne.
            dettes = []
            for row in lignes('dette'):
                fournisseur = fournisseur_par_codefour.get(row['CODEF'])
                if fournisseur is None:
                    avertissements.append(f"Dette #{row['CODED']} ignoree (fournisseur introuvable).")
                    continue
                dettes.append(DetteFournisseur(
                    entreprise=entreprise,
                    fournisseur=fournisseur,
                    montant=row['MTNTD'],
                    date=row['DATED'],
                ))
            DetteFournisseur.objects.bulk_create(dettes, batch_size=1000)

            # --------------------------------------------------- VersementFournisseur
            versements_fournisseur = []
            for row in lignes('payement'):
                fournisseur = fournisseur_par_codefour.get(row['CODEF'])
                if fournisseur is None:
                    avertissements.append(f"Versement fournisseur #{row['CODEP']} ignore (fournisseur introuvable).")
                    continue
                versements_fournisseur.append(VersementFournisseur(
                    entreprise=entreprise,
                    fournisseur=fournisseur,
                    montant=row['MTNTP'] or 0,
                    date=row['DATEP'],
                ))
            VersementFournisseur.objects.bulk_create(versements_fournisseur, batch_size=1000)

            # ------------------------------------------------------------- Retour
            # L'ancienne table ne conserve pas l'utilisateur ayant enregistre le
            # retour : on l'attribue au premier utilisateur du dump (defaut
            # documente, a corriger manuellement si besoin).
            retours = []
            for row in lignes('retour'):
                produit = produit_par_codep.get(row['produit'])
                if produit is None:
                    avertissements.append(f"Retour #{row['Code']} ignore (produit introuvable).")
                    continue
                retours.append(Retour(
                    entreprise=entreprise,
                    produit=produit,
                    quantite=row['qte'],
                    date=row['date'],
                    user=premier_user,
                    prix=row['prix'],
                ))
            Retour.objects.bulk_create(retours, batch_size=1000)

            # ------------------------------------------------------------- Depense
            categorie_depense, _ = Categorie_Depense.objects.get_or_create(
                entreprise=entreprise, nom=options['categorie_depense'],
            )
            depenses = []
            for row in lignes('depense'):
                user = user_par_codeu.get(row['CODEU'])
                if user is None:
                    avertissements.append(f"Depense #{row['CODED']} ignoree (utilisateur introuvable).")
                    continue
                depenses.append(Depense(
                    entreprise=entreprise,
                    intitule=row['INTITD'].strip(),
                    quantite=row['quantite'],
                    prix=row['prix'],
                    date=row['DATED'],
                    categorie=categorie_depense,
                    user=user,
                ))
            Depense.objects.bulk_create(depenses, batch_size=1000)

            # ------------------------------------------------------------- Autrepret
            # Ancienne table de prets "hors client" (juste un nom en texte libre,
            # sans lien vers la table client) : importee en PretClient sans client
            # rattache, le nom d'origine etant conserve dans le commentaire pour ne
            # pas le perdre.
            autre_prets = []
            for row in lignes('autrepret'):
                user = user_par_codeu.get(row['CODEU'])
                if user is None:
                    avertissements.append(f"Autre pret #{row['CODEPR']} ignore (utilisateur introuvable).")
                    continue
                commande = commande_par_codev.get(row['NumVente']) if row['NumVente'] else None
                nom = _texte(row['NOMCLI'])
                commentaire_origine = _texte(row['Commentaire'])
                commentaire = " - ".join(p for p in (nom, commentaire_origine) if p) or None
                if commentaire:
                    commentaire = commentaire[:50]
                autre_prets.append(PretClient(
                    entreprise=entreprise,
                    client=None,
                    montant=row['MTNTPR'],
                    date=row['DATEPR'],
                    dateEcheance=row['DATEECH'],
                    payer=row['PAYER'].strip(),
                    commande=commande,
                    user=user,
                    commentaire=commentaire,
                ))
            PretClient.objects.bulk_create(autre_prets, batch_size=1000)

            if dry_run:
                transaction.set_rollback(True)

        for avert in avertissements:
            self.stdout.write(self.style.WARNING(avert))

        self.stdout.write(self.style.SUCCESS(
            f"Utilisateurs : {len(user_par_codeu)} (dont {len(comptes_crees)} nouveaux).\n"
            f"Societes : {len(societe_par_numero)}.\n"
            f"Clients : {len(client_par_codecl)}.\n"
            f"Fournisseurs : {len(fournisseur_par_codefour)}.\n"
            f"Categories : {len(categorie_par_codet)}.\n"
            f"Produits : {len(produit_par_codep)}.\n"
            f"Livraisons : {len(livraison_par_codeliv)} ({len(livraison_produits)} lignes).\n"
            f"Ventes : {len(commande_par_codev)} ({len(commande_produits)} lignes).\n"
            f"Prets clients : {len(prets)}.\n"
            f"Versements clients : {len(versements_client)}.\n"
            f"Dettes fournisseurs : {len(dettes)}.\n"
            f"Versements fournisseurs : {len(versements_fournisseur)}.\n"
            f"Retours : {len(retours)}.\n"
            f"Depenses : {len(depenses)} (categorie \"{options['categorie_depense']}\").\n"
            f"Autres prets (sans client) : {len(autre_prets)}."
            + (" [DRY RUN, rien n'a ete ecrit en base]" if dry_run else "")
        ))

        if comptes_crees and not dry_run:
            self.stdout.write(self.style.WARNING(
                "\nComptes utilisateurs crees (mots de passe temporaires a "
                "communiquer puis a faire changer) :"
            ))
            for login, mdp in comptes_crees:
                self.stdout.write(f"  {login} : {mdp}")
