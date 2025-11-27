from django.contrib import admin
from .models import (
    Fournisseur, Livraison, LivraisonProduit, Produit, Categorie, CommandeProduit, Commande, Categorie_Depense, Depense, VersementClient, PretClient, Client, Societe,
    VersementFournisseur, DetteFournisseur, VersementGerant, InfoBoutique, Retour
)



@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom','adresse', 'telephone')
    search_fields = ('nom', 'telephone')
    list_filter = ('nom', 'telephone')
    ordering = ('nom',)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)
    list_filter = ('nom',)
    ordering = ('nom',)


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('codebare','categorie', 'libelle','quantite','prixAchat','prixDetail','prixEnGros', 'autrePrix','date','datePeremption','seuil','commentaire','quantiteTotal')
    search_fields = ('codebare', 'libelle','categorie')
    list_filter = ('codebare', 'libelle','categorie')
    ordering = ('libelle',)


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('fournisseur','date', 'montant','numeroFacture')
    search_fields = ('fournisseur', 'numeroFacture','date')
    list_filter = ('fournisseur', 'numeroFacture','date')
    ordering = ('date',)


@admin.register(LivraisonProduit)
class LivraisonProduitAdmin(admin.ModelAdmin):
    list_display = ('livraison','quantite', 'prix','prixDetail','peremption')
    search_fields = ('livraison',)
    list_filter = ('livraison',)
    ordering = ('livraison',)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('user','client', 'montant','remise','date','typeVente','typePayement',"client_uid")
    search_fields = ('client__nom', 'typeVente','typePayement')
    list_filter = ('client', 'typeVente','typePayement')
    ordering = ('date',)


@admin.register(CommandeProduit)
class CommandeProduitAdmin(admin.ModelAdmin):
    list_display = ('produit','commande','quantite','date', 'prix')
    search_fields = ('produit',)
    list_filter = ('produit','commande','date')
    ordering = ('produit','date')



@admin.register(Categorie_Depense)
class CategorieDepenseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)
    ordering = ('nom',)


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ('intitule', 'quantite', 'prix', 'date', 'categorie')
    search_fields = ('intitule', 'categorie__nom', 'agent__user__username')
    list_filter = ('date', 'categorie')
    ordering = ('-date',)



@admin.register(VersementClient)
class versementClientAdmin(admin.ModelAdmin):
    list_display = ('client', 'montant', 'date')
    search_fields = ('client', 'montant', 'date')
    list_filter = ('client', 'date')
    ordering = ('-date',)




@admin.register(PretClient)
class pretClientAdmin(admin.ModelAdmin):
    list_display = ('client', 'montant', 'date','dateEcheance','payer','commande','user','commentaire')
    search_fields = ('client', 'date', 'dateEcheance','payer','user')
    list_filter = ('client', 'date', 'dateEcheance','payer','user')
    ordering = ('-date',)




@admin.register(Client)
class clientAdmin(admin.ModelAdmin):
    list_display = ('societe', 'nom', 'telephone','adresse','email','matricule','pourcentage','detteMaximale')
    search_fields = ('societe', 'nom', 'telephone','adresse','matricule')
    list_filter = ('societe', 'nom', 'telephone','adresse','matricule')




@admin.register(Societe)
class societeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'adresse', 'telephone')
    search_fields = ('nom', 'telephone')
    list_filter = ('nom', 'telephone')





@admin.register(VersementFournisseur)
class versementFournisseurAdmin(admin.ModelAdmin):
    list_display = ('fournisseur', 'montant', 'date')
    search_fields = ('fournisseur', 'montant', 'date')
    list_filter = ('fournisseur', 'date')
    ordering = ('-date',)




@admin.register(DetteFournisseur)
class detteFournisseurAdmin(admin.ModelAdmin):
    list_display = ('fournisseur', 'montant', 'date')
    search_fields = ('fournisseur', 'montant', 'date')
    list_filter = ('fournisseur', 'date')
    ordering = ('-date',)





@admin.register(VersementGerant)
class versementGerantAdmin(admin.ModelAdmin):
    list_display = ('user', 'montant', 'date')
    search_fields = ('user', 'montant', 'date')
    list_filter = ('user', 'date')
    ordering = ('-date',)



@admin.register(InfoBoutique)
class infoBoutiqueAdmin(admin.ModelAdmin):
    list_display=('nom', 'emplacement','ville','telephone','proprietaire')
    search_fields=('nom', 'emplacement','ville','telephone','proprietaire') 
    list_filter=('nom','telephone','proprietaire')
    ordering=('nom',)



@admin.register(Retour)
class retourAdmin(admin.ModelAdmin):
    list_display = ('produit', 'quantite', 'date', 'prix', 'user')
    search_fields = ('produit__libelle', 'quantite', 'date')
    list_filter = ('produit__libelle', 'date')
    ordering = ('-date',)