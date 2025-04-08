from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),
    path('password_change/', views.change_password, name='password_change'),
    path('password_change/done/', views.password_change_done, name='password_change_done'),
]
