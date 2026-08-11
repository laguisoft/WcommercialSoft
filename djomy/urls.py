from django.urls import path

from . import views

urlpatterns = [
    path('abonnement/renouveler/', views.renouveler_abonnement, name='djomy_renouveler'),
    path('abonnement/historique/', views.historique_paiements, name='djomy_historique'),
    path('abonnement/retour/<str:reference>/', views.retour_paiement, name='djomy_retour'),
    path('webhook/', views.webhook, name='djomy_webhook'),
]
