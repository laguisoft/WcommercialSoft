from django.urls import path

from . import views

urlpatterns = [
    path('compte-non-rattache/', views.compte_non_rattache, name='compte_non_rattache'),
]
