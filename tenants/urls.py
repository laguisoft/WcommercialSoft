from django.urls import path

from . import views

urlpatterns = [
    path('compte-non-rattache/', views.compte_non_rattache, name='compte_non_rattache'),
    path('choisir-entreprise/', views.choisir_entreprise, name='choisir_entreprise'),
    path('contrat-expire/', views.contrat_expire, name='contrat_expire'),
    path('entreprises/<int:entreprise_id>/supprimer/', views.supprimer_entreprise, name='supprimer_entreprise'),
]
