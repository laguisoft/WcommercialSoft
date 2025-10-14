from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.create_user_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    #path('', views.home, name='home'),
    path('', views.login_view, name='login'),
    path('password_change/', views.change_password, name='password_change'),
    path('password_change/done/', views.password_change_done, name='password_change_done'),

    path('users/modifier/<int:user_id>/', views.modifier_user, name='modifier_user'),
    path('users/supprimer/<int:user_id>/', views.supprimer_user, name='supprimer_user'),
]
