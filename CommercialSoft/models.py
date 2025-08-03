from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission, User
from django.utils import timezone
from django.conf import settings
# Create your models here.




class Fournisseur(models.Model):
    nom=models.CharField(max_length=30, unique=True)
    adresse=models.CharField(max_length=30)
    telephone=models.CharField(max_length=20)

    def __str__(self):
        return self.nom
    

class Categorie(models.Model):
    nom=models.CharField(max_length=40, unique=True)

    def __str__(self):
        return self.nom


class Produit(models.Model):
    codebare=models.CharField(max_length=100, unique=True)
    categorie=models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True)
    libelle=models.CharField(max_length=60, unique=True)
    quantite=models.IntegerField()
    prixAchat=models.PositiveBigIntegerField()
    prixDetail=models.PositiveBigIntegerField()
    prixEnGros=models.PositiveBigIntegerField()
    date=models.DateField(default=timezone.now)
    datePeremption=models.DateField(default=timezone.now)
    seuil=models.PositiveIntegerField(default=0)
    commentaire=models.CharField(max_length=60, null=True, blank=True)
    quantiteTotal=models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return self.libelle


class Livraison(models.Model):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
    date=models.DateField(default=timezone.now)
    montant=models.BigIntegerField()
    numeroFacture=models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.fournisseur.nom


class LivraisonProduit(models.Model):
    livraison=models.ForeignKey(Livraison, on_delete=models.CASCADE)
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    prix=models.PositiveBigIntegerField() 
    prixDetail=models.PositiveBigIntegerField()
    peremption=models.DateField(default=timezone.now)


class Societe(models.Model):
    nom=models.CharField(max_length=30, unique=True)
    adresse=models.CharField(max_length=30, null=True, blank=True)
    telephone=models.CharField(max_length=20)

    def __str__(self):
        return self.nom
    

class Client(models.Model):
    societe=models.ForeignKey(Societe, on_delete=models.CASCADE, null=True)
    nom=models.CharField(max_length=70, unique=True)
    telephone=models.CharField(max_length=20,null=True,blank=True)
    adresse=models.CharField(max_length=30, null=True, blank=True)
    email=models.EmailField(max_length=50, null=True, blank=True)
    matricule=models.CharField(max_length=20,null=True, blank=True)
    pourcentage=models.PositiveSmallIntegerField()
    detteMaximale=models.PositiveBigIntegerField()

    def __str__(self):
        return self.nom
    

class Commande(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client=models.ForeignKey(Client, on_delete=models.SET_NULL, null=True)
    montant=models.PositiveBigIntegerField()
    remise=models.PositiveBigIntegerField(default=0)
    date=models.DateField(default=timezone.now)
    typeVente=models.CharField(max_length=15, default="detail", choices=[('detail','Detail'),('en gros','En gros')])
    typePayement=models.CharField(max_length=15, default="Espece", choices=[('Espece','Espece'),('Pret','Pret'),('Don','Don')])
    montantAchat=models.PositiveBigIntegerField()

    def __str__(self):
        return str(self.montant)


class CommandeProduit(models.Model):
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE, null=True)
    commande=models.ForeignKey(Commande, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now)
    prix=models.PositiveBigIntegerField()

    class Meta:
        unique_together = ['produit', 'commande'] 

 


 
class Categorie_Depense(models.Model):
    nom=models.CharField(max_length=30)
    description=models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.nom




class Depense(models.Model):
    intitule=models.CharField(max_length=60)
    quantite=models.PositiveIntegerField()
    prix=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now)
    categorie=models.ForeignKey(Categorie_Depense, on_delete=models.CASCADE)




class VersementClient(models.Model):
    client=models.ForeignKey(Client, on_delete=models.CASCADE, related_name='versements')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now)




class PretClient(models.Model):
    client=models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='prets')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now)
    dateEcheance=models.DateField(default=timezone.now)
    payer=models.CharField(max_length=5, choices=[('Non','Non'),('Oui','Oui')], default='Non')
    commande=models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    commentaire=models.CharField(max_length=50, null=True, blank=True)





class DetteFournisseur(models.Model):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name='detteFournisseur')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now)
    facture=models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='livraison', null=True, blank=True)



class VersementFournisseur(models.Model):
    fournisseur=models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name='versementFournisseur')
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now)



class VersementGerant(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    montant=models.BigIntegerField()
    date=models.DateField(default=timezone.now)



class InfoBoutique(models.Model):
    nom=models.CharField(max_length=30, unique=True)
    emplacement=models.CharField(max_length=30, null=True, blank=True)
    ville=models.CharField(max_length=30)
    telephone=models.CharField(max_length=20, null=True, blank=True)
    email=models.EmailField(max_length=50, null=True, blank=True)
    proprietaire=models.CharField(max_length=50, null=True, blank=True) 

    def __str__(self):
        return self.nom
    


class Retour(models.Model):
    produit=models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite=models.PositiveIntegerField()
    date=models.DateField(default=timezone.now)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prix=models.PositiveBigIntegerField()

    def __str__(self):
        return f"{self.produit.libelle} - {self.quantite} - {self.date}"