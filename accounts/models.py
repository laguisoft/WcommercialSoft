from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Le nom d’utilisateur est obligatoire')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    entreprise = models.ForeignKey(
        'tenants.Entreprise', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='utilisateurs',
    )
    entreprises_additionnelles = models.ManyToManyField(
        'tenants.Entreprise', blank=True, related_name='utilisateurs_additionnels',
        help_text="Entreprises supplémentaires accessibles à cet utilisateur, en plus de son entreprise principale.",
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.first_name+ " "+self.last_name

    def entreprises_accessibles(self):
        """Toutes les entreprises consultables par cet utilisateur (principale + additionnelles)."""
        Entreprise = self.entreprises_additionnelles.model
        ids = set(self.entreprises_additionnelles.values_list('id', flat=True))
        if self.entreprise_id:
            ids.add(self.entreprise_id)
        return Entreprise.objects.filter(id__in=ids)
