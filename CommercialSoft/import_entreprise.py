"""Import d'un paquet exporte depuis la branche main (voir CommercialSoft.export_entreprise
sur main) vers une entreprise (tenant) de la branche Saas.

Principes :
- Jamais d'ecrasement d'une donnee existante du tenant cible : les objets de
  reference (fournisseur, categorie, societe, client, produit, categorie de
  depense/decaissement) sont reutilises s'ils existent deja (meme nom), sinon
  crees. Les objets d'historique (ventes, livraisons, versements, prets,
  depenses, decaissements, dettes, retours) sont toujours crees en tant que
  nouvelles lignes rattachees a l'entreprise cible.
- Jamais de reutilisation d'un ancien identifiant (pk) : chaque objet est
  recree, les references sont resolues via une table de correspondance
  ancien-pk -> nouvel objet, construite au fur et a mesure de l'import.
- Les comptes utilisateurs ne sont jamais recrees automatiquement : l'appelant
  fournit un mapping explicite (ancien pk -> utilisateur Saas existant, ou
  demande de creation d'un nouveau compte), verifie avant l'import reel.
- InfoBoutique n'est jamais importe automatiquement (fusionne dans Entreprise
  cote Saas) : ne jamais ecraser les informations deja saisies pour le
  tenant. Les valeurs sont seulement remontees pour information.
"""
from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.crypto import get_random_string

from tenants.managers import get_current_entreprise, set_current_entreprise

from .models import (
    Categorie,
    Categorie_Decaissement,
    Categorie_Depense,
    Client,
    ClientSpecial,
    Commande,
    CommandeClient,
    CommandeClientProduit,
    CommandeProduit,
    Decaissement,
    Depense,
    DetteFournisseur,
    Fournisseur,
    ImportJournal,
    Livraison,
    LivraisonProduit,
    PretClient,
    Produit,
    Retour,
    Societe,
    VersementClient,
    VersementFournisseur,
    VersementGerant,
)

MODELE_UTILISATEUR = 'accounts.customuser'


def _force_entreprise_courante(func):
    """Force le thread-local TenantManager sur l'entreprise cible pour toute
    la duree de l'appel : sans ca, les requetes explicitement filtrees par
    entreprise= dans ce module seraient combinees (AND) avec une eventuelle
    'entreprise courante' differente deja en session (ex : superadmin qui
    navigue une autre entreprise dans le meme onglet), faussant silencieusement
    la detection des doublons."""
    @wraps(func)
    def wrapper(paquet, entreprise, *args, **kwargs):
        precedente = get_current_entreprise()
        set_current_entreprise(entreprise)
        try:
            return func(paquet, entreprise, *args, **kwargs)
        finally:
            set_current_entreprise(precedente)
    return wrapper


def _objets_par_modele(paquet):
    """Regroupe les objets du paquet par label de modele (en minuscules)."""
    groupes = {}
    for obj in paquet.get('objets', []):
        groupes.setdefault(obj['model'].lower(), []).append(obj)
    return groupes


def extraire_utilisateurs(paquet):
    """Retourne la liste des utilisateurs historiques (accounts.customuser) du paquet."""
    return [o for o in paquet.get('objets', []) if o['model'].lower() == MODELE_UTILISATEUR]


def deja_importe(entreprise, empreinte_sha256):
    return ImportJournal.objects.filter(entreprise=entreprise, empreinte_sha256=empreinte_sha256).exists()


@_force_entreprise_courante
def analyser(paquet, entreprise):
    """Dry-run : construit un rapport (sans rien ecrire) des conflits et de ce
    qui sera cree/reutilise, pour affichage avant confirmation."""
    groupes = _objets_par_modele(paquet)
    rapport = {
        'deja_importe': deja_importe(entreprise, paquet.get('empreinte_sha256', '')),
        'utilisateurs': [],
        'conflits': [],
        'a_creer': {},
    }

    for label, objets in groupes.items():
        rapport['a_creer'][label] = len(objets)

    produits = groupes.get('commercialsoft.produit', [])
    for obj in produits:
        libelle = obj['fields'].get('libelle')
        if libelle and Produit.objects.filter(entreprise=entreprise, libelle=libelle).exists():
            rapport['conflits'].append(
                f"Produit \"{libelle}\" existe deja pour cette entreprise : sera reutilise, pas duplique."
            )

    clients = groupes.get('commercialsoft.client', [])
    for obj in clients:
        nom = obj['fields'].get('nom')
        if nom and Client.objects.filter(entreprise=entreprise, nom=nom).exists():
            rapport['conflits'].append(
                f"Client \"{nom}\" existe deja pour cette entreprise : sera reutilise, pas duplique."
            )

    User = get_user_model()
    for obj in extraire_utilisateurs(paquet):
        rapport['utilisateurs'].append({
            'ancien_pk': obj['pk'],
            'username': obj['fields']['username'],
            'nom_complet': f"{obj['fields'].get('first_name', '')} {obj['fields'].get('last_name', '')}".strip(),
            'login_disponible': not User.objects.filter(username=obj['fields']['username']).exists(),
        })

    if 'commercialsoft.infoboutique' in groupes:
        rapport['info_boutique_non_importee'] = groupes['commercialsoft.infoboutique'][0]['fields']

    return rapport


def _nom_utilisateur_disponible(username):
    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        return username
    for i in range(2, 1000):
        candidat = f"{username}{i}"
        if not User.objects.filter(username=candidat).exists():
            return candidat
    raise ValueError(f"Impossible de trouver un login disponible derive de '{username}'")


def _resoudre_utilisateurs(paquet, entreprise, mapping_utilisateurs):
    """Construit users_map (ancien pk -> objet CustomUser Saas) a partir du
    mapping fourni par l'operateur (lier a un compte existant, ou creer un
    nouveau compte avec mot de passe temporaire)."""
    User = get_user_model()
    users_map = {}
    mots_de_passe_generes = {}

    for obj in extraire_utilisateurs(paquet):
        ancien_pk = obj['pk']
        choix = mapping_utilisateurs.get(str(ancien_pk)) or mapping_utilisateurs.get(ancien_pk)
        if not choix:
            raise ValueError(f"Aucun mapping fourni pour l'utilisateur historique '{obj['fields']['username']}'.")

        if choix.get('action') == 'lier':
            utilisateur = User.objects.get(pk=choix['user_id'])
        elif choix.get('action') == 'creer':
            username = _nom_utilisateur_disponible(obj['fields']['username'])
            mot_de_passe = get_random_string(12)
            utilisateur = User.objects.create_user(
                username=username,
                password=mot_de_passe,
                first_name=obj['fields'].get('first_name', ''),
                last_name=obj['fields'].get('last_name', ''),
                is_active=obj['fields'].get('is_active', True),
                entreprise=entreprise,
            )
            for nom_groupe in obj['fields'].get('groupes', []):
                groupe, _ = Group.objects.get_or_create(name=nom_groupe)
                utilisateur.groups.add(groupe)
            mots_de_passe_generes[username] = mot_de_passe
        else:
            raise ValueError(f"Action de mapping inconnue pour l'utilisateur '{obj['fields']['username']}'.")

        users_map[ancien_pk] = utilisateur

    return users_map, mots_de_passe_generes


@transaction.atomic
@_force_entreprise_courante
def executer(paquet, entreprise, mapping_utilisateurs, importe_par):
    """Realise l'import complet, dans une seule transaction : soit tout est
    ecrit, soit rien ne l'est en cas d'erreur."""
    empreinte = paquet.get('empreinte_sha256', '')
    if deja_importe(entreprise, empreinte):
        raise ValueError("Cet export a deja ete importe pour cette entreprise.")

    groupes = _objets_par_modele(paquet)
    rapport = {'crees': {}, 'reutilises': {}, 'ignores': {}}

    def compte(cle, dico):
        dico[cle] = dico.get(cle, 0) + 1

    users_map, mots_de_passe_generes = _resoudre_utilisateurs(paquet, entreprise, mapping_utilisateurs)
    rapport['comptes_crees'] = sorted(mots_de_passe_generes.keys())

    fournisseur_map = {}
    for obj in groupes.get('commercialsoft.fournisseur', []):
        f = obj['fields']
        existant = Fournisseur.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if existant:
            fournisseur_map[obj['pk']] = existant
            compte('commercialsoft.fournisseur', rapport['reutilises'])
        else:
            fournisseur_map[obj['pk']] = Fournisseur.objects.create(
                entreprise=entreprise, nom=f['nom'], adresse=f.get('adresse', ''), telephone=f.get('telephone', ''),
            )
            compte('commercialsoft.fournisseur', rapport['crees'])

    categorie_map = {}
    for obj in groupes.get('commercialsoft.categorie', []):
        existant = Categorie.objects.filter(entreprise=entreprise, nom=obj['fields']['nom']).first()
        if existant:
            categorie_map[obj['pk']] = existant
            compte('commercialsoft.categorie', rapport['reutilises'])
        else:
            categorie_map[obj['pk']] = Categorie.objects.create(entreprise=entreprise, nom=obj['fields']['nom'])
            compte('commercialsoft.categorie', rapport['crees'])

    societe_map = {}
    for obj in groupes.get('commercialsoft.societe', []):
        f = obj['fields']
        existant = Societe.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if existant:
            societe_map[obj['pk']] = existant
            compte('commercialsoft.societe', rapport['reutilises'])
        else:
            societe_map[obj['pk']] = Societe.objects.create(
                entreprise=entreprise, nom=f['nom'], adresse=f.get('adresse'), telephone=f.get('telephone', ''),
            )
            compte('commercialsoft.societe', rapport['crees'])

    produit_map = {}
    for obj in groupes.get('commercialsoft.produit', []):
        f = obj['fields']
        existant = Produit.objects.filter(entreprise=entreprise, libelle=f['libelle']).first()
        if existant:
            produit_map[obj['pk']] = existant
            compte('commercialsoft.produit', rapport['reutilises'])
            continue

        codebare = f.get('codebare') or None
        if codebare and Produit.objects.filter(entreprise=entreprise, codebare=codebare).exists():
            codebare = None

        produit_map[obj['pk']] = Produit.objects.create(
            entreprise=entreprise,
            codebare=codebare,
            categorie=categorie_map.get(f.get('categorie')),
            libelle=f['libelle'],
            quantite=f['quantite'],
            prixAchat=f['prixAchat'],
            prixEnGros=f['prixEnGros'],
            prixDetail=f['prixDetail'],
            autrePrix=f.get('autrePrix', 0),
            date=f['date'],
            datePeremption=f['datePeremption'],
            seuil=f.get('seuil', 0),
            commentaire=f.get('commentaire'),
            quantiteTotal=f.get('quantiteTotal', 0),
            special=f.get('special', False),
        )
        compte('commercialsoft.produit', rapport['crees'])

    client_map = {}
    for obj in groupes.get('commercialsoft.client', []):
        f = obj['fields']
        existant = Client.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if existant:
            client_map[obj['pk']] = existant
            compte('commercialsoft.client', rapport['reutilises'])
            continue

        client_map[obj['pk']] = Client.objects.create(
            entreprise=entreprise,
            societe=societe_map.get(f.get('societe')),
            nom=f['nom'],
            telephone=f.get('telephone'),
            adresse=f.get('adresse'),
            email=f.get('email'),
            matricule=f.get('matricule'),
            pourcentage=f.get('pourcentage', 0),
            detteMaximale=f.get('detteMaximale', 0),
        )
        compte('commercialsoft.client', rapport['crees'])

    clientspecial_map = {}
    for obj in groupes.get('commercialsoft.clientspecial', []):
        f = obj['fields']
        existant = ClientSpecial.objects.filter(entreprise=entreprise, telephone=f['telephone']).first()
        if existant:
            clientspecial_map[obj['pk']] = existant
            compte('commercialsoft.clientspecial', rapport['reutilises'])
        else:
            clientspecial_map[obj['pk']] = ClientSpecial.objects.create(
                entreprise=entreprise, nom=f['nom'], prenom=f.get('prenom'), telephone=f['telephone'],
            )
            compte('commercialsoft.clientspecial', rapport['crees'])

    categorie_depense_map = {}
    for obj in groupes.get('commercialsoft.categorie_depense', []):
        f = obj['fields']
        existant = Categorie_Depense.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if existant:
            categorie_depense_map[obj['pk']] = existant
            compte('commercialsoft.categorie_depense', rapport['reutilises'])
        else:
            categorie_depense_map[obj['pk']] = Categorie_Depense.objects.create(
                entreprise=entreprise, nom=f['nom'], description=f.get('description'),
            )
            compte('commercialsoft.categorie_depense', rapport['crees'])

    categorie_decaissement_map = {}
    for obj in groupes.get('commercialsoft.categorie_decaissement', []):
        f = obj['fields']
        existant = Categorie_Decaissement.objects.filter(entreprise=entreprise, nom=f['nom']).first()
        if existant:
            categorie_decaissement_map[obj['pk']] = existant
            compte('commercialsoft.categorie_decaissement', rapport['reutilises'])
        else:
            categorie_decaissement_map[obj['pk']] = Categorie_Decaissement.objects.create(
                entreprise=entreprise, nom=f['nom'], description=f.get('description'),
            )
            compte('commercialsoft.categorie_decaissement', rapport['crees'])

    livraison_map = {}
    for obj in groupes.get('commercialsoft.livraison', []):
        f = obj['fields']
        client_uid = f.get('client_uid') or None
        if client_uid and Livraison.objects.filter(entreprise=entreprise, client_uid=client_uid).exists():
            livraison_map[obj['pk']] = Livraison.objects.get(entreprise=entreprise, client_uid=client_uid)
            compte('commercialsoft.livraison', rapport['reutilises'])
            continue
        livraison_map[obj['pk']] = Livraison.objects.create(
            entreprise=entreprise,
            fournisseur=fournisseur_map.get(f['fournisseur']),
            date=f['date'],
            montant=f['montant'],
            numeroFacture=f.get('numeroFacture'),
            typePayement=f.get('typePayement', 'Espece'),
            client_uid=client_uid,
        )
        compte('commercialsoft.livraison', rapport['crees'])

    for obj in groupes.get('commercialsoft.livraisonproduit', []):
        f = obj['fields']
        livraison = livraison_map.get(f['livraison'])
        produit = produit_map.get(f['produit'])
        if not livraison or not produit:
            compte('commercialsoft.livraisonproduit', rapport['ignores'])
            continue
        LivraisonProduit.objects.create(
            entreprise=entreprise, livraison=livraison, produit=produit,
            quantite=f['quantite'], prix=f['prix'], prixEnGros=f.get('prixEnGros', 0), prixDetail=f['prixDetail'],
            peremption=f.get('peremption'),
        )
        compte('commercialsoft.livraisonproduit', rapport['crees'])

    commande_map = {}
    for obj in groupes.get('commercialsoft.commande', []):
        f = obj['fields']
        client_uid = f.get('client_uid') or None
        if client_uid and Commande.objects.filter(entreprise=entreprise, client_uid=client_uid).exists():
            commande_map[obj['pk']] = Commande.objects.get(entreprise=entreprise, client_uid=client_uid)
            compte('commercialsoft.commande', rapport['reutilises'])
            continue
        commande_map[obj['pk']] = Commande.objects.create(
            entreprise=entreprise,
            user=users_map[f['user']],
            client=client_map.get(f.get('client')),
            clientSpecial=clientspecial_map.get(f.get('clientSpecial')),
            montant=f['montant'],
            remise=f.get('remise', 0),
            date=f['date'],
            typeVente=f.get('typeVente', 'detail'),
            typePayement=f.get('typePayement', 'Espece'),
            montantAchat=f.get('montantAchat', 0),
            client_uid=client_uid,
        )
        compte('commercialsoft.commande', rapport['crees'])

    for obj in groupes.get('commercialsoft.commandeproduit', []):
        f = obj['fields']
        commande = commande_map.get(f['commande'])
        produit = produit_map.get(f.get('produit'))
        if not commande:
            compte('commercialsoft.commandeproduit', rapport['ignores'])
            continue
        CommandeProduit.objects.create(
            entreprise=entreprise, commande=commande, produit=produit,
            quantite=f['quantite'], date=f['date'], prix=f['prix'],
        )
        compte('commercialsoft.commandeproduit', rapport['crees'])

    commandeclient_map = {}
    for obj in groupes.get('commercialsoft.commandeclient', []):
        f = obj['fields']
        client = client_map.get(f['client'])
        if not client:
            compte('commercialsoft.commandeclient', rapport['ignores'])
            continue
        commandeclient_map[obj['pk']] = CommandeClient.objects.create(
            entreprise=entreprise,
            client=client,
            date=f['date'],
            statut=f.get('statut', 'En attente'),
            commentaire=f.get('commentaire'),
            motifRejet=f.get('motifRejet'),
            commande=commande_map.get(f.get('commande')),
            traitePar=users_map.get(f.get('traitePar')),
            dateTraitement=f.get('dateTraitement'),
        )
        compte('commercialsoft.commandeclient', rapport['crees'])

    for obj in groupes.get('commercialsoft.commandeclientproduit', []):
        f = obj['fields']
        demande = commandeclient_map.get(f['demande'])
        produit = produit_map.get(f.get('produit'))
        if not demande or not produit:
            compte('commercialsoft.commandeclientproduit', rapport['ignores'])
            continue
        CommandeClientProduit.objects.create(
            entreprise=entreprise, demande=demande, produit=produit,
            quantiteDemandee=f['quantiteDemandee'], quantiteAcceptee=f.get('quantiteAcceptee'),
            prixUnitaire=f['prixUnitaire'],
        )
        compte('commercialsoft.commandeclientproduit', rapport['crees'])

    for obj in groupes.get('commercialsoft.depense', []):
        f = obj['fields']
        Depense.objects.create(
            entreprise=entreprise,
            intitule=f['intitule'], quantite=f['quantite'], prix=f['prix'], date=f['date'],
            categorie=categorie_depense_map.get(f['categorie']),
            user=users_map[f['user']],
        )
        compte('commercialsoft.depense', rapport['crees'])

    for obj in groupes.get('commercialsoft.decaissement', []):
        f = obj['fields']
        Decaissement.objects.create(
            entreprise=entreprise,
            motif=f['motif'], montant=f['montant'], date=f['date'],
            categorie=categorie_decaissement_map.get(f['categorie']),
            user=users_map[f['user']],
        )
        compte('commercialsoft.decaissement', rapport['crees'])

    for obj in groupes.get('commercialsoft.versementclient', []):
        f = obj['fields']
        client = client_map.get(f['client'])
        if not client:
            compte('commercialsoft.versementclient', rapport['ignores'])
            continue
        VersementClient.objects.create(
            entreprise=entreprise, client=client, montant=f['montant'], date=f['date'], user=users_map[f['user']],
        )
        compte('commercialsoft.versementclient', rapport['crees'])

    for obj in groupes.get('commercialsoft.pretclient', []):
        f = obj['fields']
        PretClient.objects.create(
            entreprise=entreprise,
            client=client_map.get(f.get('client')),
            montant=f['montant'], date=f['date'], dateEcheance=f['dateEcheance'], payer=f.get('payer', 'Non'),
            commande=commande_map.get(f.get('commande')),
            user=users_map[f['user']],
            commentaire=f.get('commentaire'),
        )
        compte('commercialsoft.pretclient', rapport['crees'])

    for obj in groupes.get('commercialsoft.dettefournisseur', []):
        f = obj['fields']
        fournisseur = fournisseur_map.get(f['fournisseur'])
        if not fournisseur:
            compte('commercialsoft.dettefournisseur', rapport['ignores'])
            continue
        DetteFournisseur.objects.create(
            entreprise=entreprise, fournisseur=fournisseur, montant=f['montant'], date=f['date'],
            facture=livraison_map.get(f.get('facture')),
        )
        compte('commercialsoft.dettefournisseur', rapport['crees'])

    for obj in groupes.get('commercialsoft.versementfournisseur', []):
        f = obj['fields']
        fournisseur = fournisseur_map.get(f['fournisseur'])
        if not fournisseur:
            compte('commercialsoft.versementfournisseur', rapport['ignores'])
            continue
        VersementFournisseur.objects.create(
            entreprise=entreprise, fournisseur=fournisseur, montant=f['montant'], date=f['date'],
        )
        compte('commercialsoft.versementfournisseur', rapport['crees'])

    for obj in groupes.get('commercialsoft.versementgerant', []):
        f = obj['fields']
        VersementGerant.objects.create(
            entreprise=entreprise, user=users_map[f['user']], montant=f['montant'], date=f['date'],
        )
        compte('commercialsoft.versementgerant', rapport['crees'])

    for obj in groupes.get('commercialsoft.retour', []):
        f = obj['fields']
        produit = produit_map.get(f.get('produit'))
        if not produit:
            compte('commercialsoft.retour', rapport['ignores'])
            continue
        Retour.objects.create(
            entreprise=entreprise, produit=produit, quantite=f['quantite'], date=f['date'],
            user=users_map[f['user']], prix=f['prix'],
        )
        compte('commercialsoft.retour', rapport['crees'])

    if 'commercialsoft.infoboutique' in groupes:
        rapport['info_boutique_non_importee'] = groupes['commercialsoft.infoboutique'][0]['fields']

    ImportJournal.objects.create(
        entreprise=entreprise,
        empreinte_sha256=empreinte,
        importe_par=importe_par,
        rapport=rapport,
    )

    return rapport
