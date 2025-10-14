from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import Group, Permission
from .models import CustomUser
from django.contrib.auth.forms import UserChangeForm
from collections import OrderedDict




# --- utilitaires libellés FR ---
def french_label_from_codename(codename: str) -> str:
    # ex: add_produit -> "Ajouter produit"
    mapping = {
        "add_": "Ajouter ",
        "change_": "Modifier ",
        "delete_": "Supprimer ",
        "view_": "Voir ",
    }
    for prefix, fr in mapping.items():
        if codename.startswith(prefix):
            return fr + codename[len(prefix):].replace("_", " ")
    return codename.replace("_", " ")

def beautify_model_name(raw_model: str) -> str:
    # ex: "ligne_vente" -> "Ligne vente"
    return raw_model.replace("_", " ").capitalize()

class CustomUserCreationForm(UserCreationForm):
    
    first_name = forms.CharField(
        max_length=150, label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150, label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    groupes = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        label="Groupes",
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2bs4'})
    )

    # ✅ permissions directes (uniquement CommercialSoft), affichées en checkbox (rendu custom dans le template)
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(content_type__app_label='CommercialSoft').order_by(
            'content_type__model', 'codename'
        ),
        label="Permissions (CommercialSoft)",
        required=False,
        widget=forms.CheckboxSelectMultiple  # on rendra manuellement
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'groupes', 'permissions')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # --- propriétés alimentées pour le template ---
    grouped_permissions: OrderedDict = None  # { 'produit': [ (id, 'Ajouter produit'), ... ], ... }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Styliser les mots de passe
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Mot de passe'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmer le mot de passe'})

        # Construire le mapping module -> permissions (FR)
        grouped = OrderedDict()
        for perm in self.fields['permissions'].queryset:
            model_key = perm.content_type.model  # ex: 'produit', 'vente', ...
            label_fr = french_label_from_codename(perm.codename)
            grouped.setdefault(model_key, []).append((perm.id, label_fr))

        # trier lisiblement par action (Voir, Ajouter, Modifier, Supprimer)
        order_keys = ("view ", "Ajouter", "Modifier", "Supprimer")
        def sort_perm(item):
            _id, txt = item
            t = txt.lower()
            # forcer ordre: voir, ajouter, modifier, supprimer
            if t.startswith("voir"):
                return (0, t)
            if t.startswith("ajouter"):
                return (1, t)
            if t.startswith("modifier"):
                return (2, t)
            if t.startswith("supprimer"):
                return (3, t)
            return (4, t)

        for k in list(grouped.keys()):
            grouped[k] = sorted(grouped[k], key=sort_perm)

        self.grouped_permissions = grouped  # utilisé dans le template

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Groupes
            user.groups.set(self.cleaned_data.get("groupes", []))
            # Permissions directes
            user.user_permissions.set(self.cleaned_data.get("permissions", []))
        return user







def french_label_from_codename(codename: str):
    mapping = {
        "add_": "Ajouter ",
        "change_": "Modifier ",
        "delete_": "Supprimer ",
        "view_": "Voir ",
    }
    for prefix, fr in mapping.items():
        if codename.startswith(prefix):
            return fr + codename[len(prefix):].replace("_", " ")
    return codename.replace("_", " ")

def beautify_model_name(raw_model: str):
    return raw_model.replace("_", " ").capitalize()

class CustomUserModificationForm(UserChangeForm):
    password = None  # Masquer le champ password

    first_name = forms.CharField(
        max_length=150,
        label="Prénom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    groupes = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        label="Groupes",
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2bs4'})
    )

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(content_type__app_label='CommercialSoft')
                                   .order_by('content_type__model', 'codename'),
        label="Permissions (CommercialSoft)",
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'groupes', 'permissions')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    grouped_permissions = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-remplir les permissions existantes de l'utilisateur
        if self.instance and self.instance.pk:
            self.initial['permissions'] = list(
            self.instance.user_permissions.values_list('id', flat=True)
        )

        # Construire les groupes de permissions
        grouped = OrderedDict()
        for perm in self.fields['permissions'].queryset:
            model_key = perm.content_type.model
            label_fr = french_label_from_codename(perm.codename)
            grouped.setdefault(model_key, []).append((perm.id, label_fr))

        def sort_perm(item):
            _id, txt = item
            t = txt.lower()
            if t.startswith("voir"):
                return (0, t)
            if t.startswith("ajouter"):
                return (1, t)
            if t.startswith("modifier"):
                return (2, t)
            if t.startswith("supprimer"):
                return (3, t)
            return (4, t)

        for k in list(grouped.keys()):
            grouped[k] = sorted(grouped[k], key=sort_perm)

        self.grouped_permissions = grouped

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.groups.set(self.cleaned_data.get("groupes", []))
            user.user_permissions.set(self.cleaned_data.get("permissions", []))
        return user
    

    


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Nom d’utilisateur',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class CustomPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Ancien mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    confirm_new_password = forms.CharField(
        label="Confirmer mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_password') != cleaned_data.get('confirm_new_password'):
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data
