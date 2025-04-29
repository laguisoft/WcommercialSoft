from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
from django.contrib.auth.models import Group

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name')

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Nom d’utilisateur')




class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=150, label="Prénom")
    last_name = forms.CharField(max_length=150, label="Nom")
    groupe = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Groupe d'utilisateur",
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'groupe')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            groupe = self.cleaned_data["groupe"]
            user.groups.add(groupe)
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