from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission, User
from django.utils import timezone
from django.conf import settings

from tenants.models import TenantScopedModel
# Create your models here.




class Fournisseur(TenantScopedModel):
    nom=models.CharField(max_length=100)
    adresse=models.CharField(max_length=30)
    telephone=models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'nom'], name='fournisseur_nom_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.nom


class Categorie(TenantScopedModel):
    nom=models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'nom'], name='categorie_nom_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.nom


class Produit(TenantScopedModel):
    codebare=models.CharField(max_length=100, null=True, blank=True)
    categorie=models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True)
    libelle=models.CharField(max_length=60)
    quantite=models.IntegerField()
    prixAchat=models.DecimalField(max_digits=30, decimal_places=0)
    prixEnGros=models.DecimalField(max_digits=30, decimal_places=0)
    prixDetail=models.DecimalField(max_digits=30, decimal_places=0)
    autrePrix=models.DecimalField(max_digits=30, decimal_places=0, default=0)
    date=models.DateField(default=timezone.now)
    datePeremption=models.DateField(default=timezone.now)
    seuil=models.PositiveIntegerField(default=0)
    commentaire=models.CharField(max_length=60, null=True, blank=True)
    quantiteTotal=models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'codebare'], name='produit_codebare_unique_par_entreprise'),
            models.UniqueConstraint(fields=['entreprise', 'libelle'], name='produit_libelle_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.libelle


class Livraison(TenantScopedModel):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
    date=models.DateField(default=timezone.now, db_index=True)
    montant=models.BigIntegerField()
    numeroFacture=models.CharField(max_length=20, blank=True, null=True)
    typePayement=models.CharField(max_length=15, default="Espece", choices=[('Espece','Espece'),('Pret','Pret')])
    # pour la gestion hors ligne
    client_uid = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'client_uid'], name='livraison_client_uid_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.fournisseur.nom


class LivraisonProduit(TenantScopedModel):
    livraison=models.ForeignKey(Livraison, on_delete=models.CASCADE)
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    prix=models.PositiveBigIntegerField()
    prixEnGros=models.PositiveBigIntegerField(default=0, blank=True)
    prixDetail=models.PositiveBigIntegerField()
    peremption=models.DateField(null=True, blank=True)


class Societe(TenantScopedModel):
    nom=models.CharField(max_length=100)
    adresse=models.CharField(max_length=100, null=True, blank=True)
    telephone=models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'nom'], name='societe_nom_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.nom


class Client(TenantScopedModel):
    societe=models.ForeignKey(Societe, on_delete=models.CASCADE, null=True)
    nom=models.CharField(max_length=70)
    telephone=models.CharField(max_length=20,null=True,blank=True)
    adresse=models.CharField(max_length=30, null=True, blank=True)
    email=models.EmailField(max_length=50, null=True, blank=True)
    matricule=models.CharField(max_length=20,null=True, blank=True)
    pourcentage=models.PositiveSmallIntegerField()
    detteMaximale=models.PositiveBigIntegerField()
    # Compte du portail client, cree et lie par le gerant
    user=models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_profile')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'nom'], name='client_nom_unique_par_entreprise'),
        ]

    def __str__(self):
        return self.nom


class Commande(TenantScopedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client=models.ForeignKey(Client, on_delete=models.SET_NULL, null=True)
    montant=models.PositiveBigIntegerField()
    remise=models.PositiveBigIntegerField(default=0)
    date=models.DateTimeField(default=timezone.now, db_index=True)
    typeVente=models.CharField(max_length=15, default="detail", choices=[('detail','Detail'),('en gros','En gros')])
    typePayement=models.CharField(max_length=20, default="Espece", choices=[('Espece','Espece'),('Pret','Pret'),('Don','Don'),('Orange Money','Orange Money')])
    montantAchat=models.PositiveBigIntegerField()
    # pour la gestion hors ligne
    client_uid = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'client_uid'], name='commande_client_uid_unique_par_entreprise'),
        ]

    def __str__(self):
        return str(self.montant)


class CommandeProduit(TenantScopedModel):
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE, null=True)
    commande=models.ForeignKey(Commande, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    prix=models.PositiveBigIntegerField()

    class Meta:
        unique_together = ['produit', 'commande']


class CommandeClient(TenantScopedModel):
    """Demande de commande passee par un client depuis le portail.
    Reste 'En attente' tant qu'un employe n'a pas verifie les quantites
    disponibles et valide; la validation declenche la vente reelle (Commande)."""
    client=models.ForeignKey(Client, on_delete=models.CASCADE, related_name='demandes_commande')
    date=models.DateField(default=timezone.now, db_index=True)
    statut=models.CharField(max_length=15, default='En attente', choices=[
        ('En attente', 'En attente'),
        ('Traitee', 'Traitee'),
        ('Rejetee', 'Rejetee'),
    ])
    commentaire=models.CharField(max_length=200, null=True, blank=True)
    motifRejet=models.TextField(max_length=500, null=True, blank=True)
    commande=models.OneToOneField(Commande, on_delete=models.SET_NULL, null=True, blank=True, related_name='demande_origine')
    traitePar=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_traitees')
    dateTraitement=models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Demande #{self.id} - {self.client.nom}"


class CommandeClientProduit(TenantScopedModel):
    demande=models.ForeignKey(CommandeClient, on_delete=models.CASCADE, related_name='lignes')
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantiteDemandee=models.PositiveIntegerField()
    quantiteAcceptee=models.PositiveIntegerField(null=True, blank=True)
    prixUnitaire=models.PositiveBigIntegerField()

    class Meta:
        unique_together = ['demande', 'produit']


class Categorie_Depense(TenantScopedModel):
    nom=models.CharField(max_length=50)
    description=models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.nom




class Depense(TenantScopedModel):
    intitule=models.CharField(max_length=100)
    quantite=models.PositiveIntegerField()
    prix=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    categorie=models.ForeignKey(Categorie_Depense, on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)




class Categorie_Decaissement(TenantScopedModel):
    nom=models.CharField(max_length=50)
    description=models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.nom




class Decaissement(TenantScopedModel):
    motif=models.CharField(max_length=100)
    montant=models.PositiveBigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    categorie=models.ForeignKey(Categorie_Decaissement, on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)




class VersementClient(TenantScopedModel):
    client=models.ForeignKey(Client, on_delete=models.CASCADE, related_name='versements')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)




class PretClient(TenantScopedModel):
    client=models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='prets')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    dateEcheance=models.DateField(default=timezone.now)
    payer=models.CharField(max_length=5, choices=[('Non','Non'),('Oui','Oui')], default='Non')
    commande=models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    commentaire=models.CharField(max_length=50, null=True, blank=True)





class DetteFournisseur(TenantScopedModel):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name='detteFournisseur')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    facture=models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='livraison', null=True, blank=True)



class VersementFournisseur(TenantScopedModel):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name='versementFournisseur')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)



class VersementGerant(TenantScopedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)



class Retour(TenantScopedModel):
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now, db_index=True)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prix=models.PositiveBigIntegerField()

    def __str__(self):
        return f"{self.produit.libelle} - {self.quantite} - {self.date}"
