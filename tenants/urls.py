from django.urls import path

from . import views

urlpatterns = [
    path('compte-non-rattache/', views.compte_non_rattache, name='compte_non_rattache'),
    path('choisir-entreprise/', views.choisir_entreprise, name='choisir_entreprise'),
    path('changer-entreprise/', views.changer_entreprise, name='changer_entreprise'),
]
