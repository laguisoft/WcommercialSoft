from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name')

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Nom d’utilisateur')



class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")  # Ajout d'un champ pour l'email
    first_name = forms.CharField(max_length=150, label="Prénom")
    last_name = forms.CharField(max_length=150, label="Nom")

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email')  # Email ajouté aux champs à afficher

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]  # On enregistre l'email
        if commit:
            user.save()
        return user
    


class CustomPasswordChangeForm(forms.Form):
    old_password = forms.CharField(label="Ancien mot de passe", widget=forms.PasswordInput)
    new_password = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput)
    confirm_new_password = forms.CharField(label="Confirmer le nouveau mot de passe", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password != confirm_new_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        
        return cleaned_data