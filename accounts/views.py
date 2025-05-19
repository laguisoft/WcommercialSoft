from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from .forms import CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages



#------------------------ Gestion des droits d'acces avec les decorateur -----------------
def est_administrateur(user):
    return user.groups.filter(name='Administrateur').exists()

def est_gestionnaire(user):
    return user.groups.filter(name='Gestionnaire').exists()

def est_utilisateur(user):
    return user.groups.filter(name='Utilisateur').exists()

def est_comptable(user):
    return user.groups.filter(name='Comptable').exists()






@login_required
def register_view(request):
    form = CustomUserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('login')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    form = CustomAuthenticationForm(request, data=request.POST or None)
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('commerce_dashboard')
    return render(request, 'accounts/login.html', {'form': form})



@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    return render(request, 'accounts/home.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password']

            # Vérification de l'ancien mot de passe
            if not request.user.check_password(old_password):
                form.add_error('old_password', "L'ancien mot de passe est incorrect.")
            else:
                # Changer le mot de passe
                user = request.user
                user.set_password(new_password)
                user.save()

                # Mettre à jour la session de l'utilisateur
                update_session_auth_hash(request, user)

                messages.success(request, "Votre mot de passe a été changé avec succès.")
                return redirect('password_change_done')
    else:
        form = CustomPasswordChangeForm()

    return render(request, 'accounts/password_change.html', {'form': form})


@login_required
def password_change_done(request):
    return render(request, 'accounts/password_change_done.html')