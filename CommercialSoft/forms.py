from django import forms
from django.contrib.auth.models import User
from .models import Fournisseur, Livraison, Produit, Categorie, LivraisonProduit, Commande, CommandeProduit, Categorie_Depense, Depense, VersementClient, PretClient, Client, Societe, VersementFournisseur, DetteFournisseur, VersementGerant
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.forms import inlineformset_factory
from django.utils import timezone


# Formulaire pour la connexion
class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom d\'utilisateur',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )


# Formulaire pour le modèle fournisseur
class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = '__all__'
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Formulaire pour le modèle categorie
class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = '__all__'
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Formulaire pour le modèle produit
class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['codebare','categorie','libelle','quantite','prixAchat','prixDetail','prixEnGros','date','datePeremption','seuil','commentaire']
        widgets = {
            'codebare': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control'}),
            'prixAchat': forms.NumberInput(attrs={'class': 'form-control'}),
            'prixDetail': forms.NumberInput(attrs={'class': 'form-control'}),
            'prixEnGros': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDateEnregistrement'}),
            'datePeremption': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDatePeremption'}),
            'seuil': forms.NumberInput(attrs={'class': 'form-control'}),
            'commentaire': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Formulaire pour le modèle livraison
class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ['fournisseur','date','montant','numeroFacture']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-control select2bs4'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDate'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control','id':'numLivraison','disabled':'true'}),
            'numeroFacture': forms.TextInput(attrs={'class': 'form-control'}),
        }





# Formulaire pour le modèle livraisonProduit
class LivraisonProduitForm(forms.ModelForm):
    class Meta:
        model = LivraisonProduit
        fields = ['produit','quantite','prix','prixDetail','peremption']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idProduit"}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'id':"quantite"}),
            'prix': forms.NumberInput(attrs={'class': 'form-control','id':'prixAchat'}),
            'prixDetail': forms.NumberInput(attrs={'class': 'form-control','id':"prixDetail"}),
            'peremption': forms.TextInput(attrs={'class': 'form-control', 'id':'peremption','placeholder': 'MM/AA', 'maxlength': '5', 'inputmode': 'numeric','pattern': r'\d{2}/\d{2}','autocomplete': 'off'}),
        }



# Formulaire pour le modèle livraisonProduit
LivraisonProduitFormSet = inlineformset_factory(
    Livraison, LivraisonProduit,
    form=LivraisonProduitForm,
    extra=1, can_delete=True
)


# Formulaire pour le modèle commande
class CommandeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Si aucune valeur n’est fournie, on met la date du jour
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()

    class Meta:
        model = Commande
        fields = ['montant','remise','date','typeVente','typePayement']
        widgets = {
            'montant': forms.TextInput(attrs={'class': 'form-control','id':'netPayer',"hidden":"true",'readonly':'true'}),
            'remise': forms.NumberInput(attrs={'class': 'form-control','placeholder':'Remise','id':'remise'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idCommande'}),
            'typeVente': forms.Select(attrs={'class': 'form-control', 'id':'typeVente'}),
            'typePayement': forms.Select(attrs={'class': 'form-control','id':'typePayement'}),
        }


# Formulaire pour le modèle livraisonProduit
class CommandeProduitForm(forms.ModelForm):
    class Meta:
        model = CommandeProduit
        fields = ['produit','quantite','prix']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idProduit"}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'id':"quantite"}),
            'prix': forms.NumberInput(attrs={'class': 'form-control','id':'prixDetail'}),
        }



CommandeProduitFormSet = inlineformset_factory(
    Commande, CommandeProduit,
    form=CommandeProduitForm,
    extra=1, can_delete=True
)






# Formulaire pour le modèle Categorie Depense
class CategorieDepenseForm(forms.ModelForm):
    class Meta:
        model = Categorie_Depense
        fields = '__all__'
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }




# Formulaire pour le modèle Depense
class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['intitule','quantite','prix','categorie','date']
        widgets = {
            'intitule': forms.TextInput(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control select2bs4', 'id':'idCategorie'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDate'}),
        }





# Formulaire pour le modèle Depense
class VersementClientForm(forms.ModelForm):
    class Meta:
        model = VersementClient
        fields = ['client', 'montant', 'date']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idClient"}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDate'}),
        }





class pretClientForm(forms.ModelForm):
    class Meta:
        model = PretClient
        fields = ['client', 'dateEcheance']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control select2bs4', 'id': 'clientid'}),
            'dateEcheance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'dateEch'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].required = False
        self.fields['dateEcheance'].required = False



# Formulaire pour le modèle Depense
class detteClientForm(forms.ModelForm):
    class Meta:
        model = PretClient
        fields = ['client', 'montant', 'date','dateEcheance','commentaire']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idClient"}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id':'idDate'}),
            'dateEcheance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id':'idDateEch'}),
            'commentaire': forms.TextInput(attrs={'class': 'form-control'}),
        }

        




# Formulaire pour le modèle Depense
class clientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['societe', 'nom', 'telephone','adresse','email','matricule','pourcentage','detteMaximale']
        widgets = {
            'societe': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idClient"}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.NumberInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'pourcentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'detteMaximale': forms.NumberInput(attrs={'class': 'form-control'}),
        }




# Formulaire pour le modèle Depense
class societeForm(forms.ModelForm):
    class Meta:
        model = Societe
        fields = ['nom','adresse', 'telephone']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.NumberInput(attrs={'class': 'form-control'}),
        }





class VersementFournisseurForm(forms.ModelForm):
    class Meta:
        model = VersementFournisseur
        fields = ['fournisseur', 'montant', 'date']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idFournisseur"}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id':'idDate'}),
        }




class DetteFournisseurForm(forms.ModelForm):
    class Meta:
        model = DetteFournisseur
        fields = ['fournisseur', 'montant', 'date']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idFournisseur"}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDate'}),
        }





# Formulaire pour le modèle versement gerant
class VersementGerantForm(forms.ModelForm):
    class Meta:
        model = VersementGerant
        fields = ['user', 'montant', 'date']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control select2bs4', "id":"idUser"}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date','id':'idDate'}),
        }





# charger un fichier excel
CHOIX_TABLES = [
    ("societe", "Société"),
    ("client", "Client"),
    ("produit", "Produit"),
]

class UploadFileForm(forms.Form):
    table = forms.ChoiceField(choices=CHOIX_TABLES, label="Table de destination")
    fichier = forms.FileField(label="Choisir un fichier Excel")