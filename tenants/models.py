from django.db import models
from django.utils.text import slugify

from .managers import TenantManager


class Entreprise(models.Model):
    """Le tenant : une entreprise/boutique cliente de la plateforme SaaS.

    Reprend les champs de l'ancien modèle CommercialSoft.InfoBoutique
    (fusionné ici) afin que les templates existants ({{ boutique.nom }},
    {{ boutique.ville }}, ...) continuent de fonctionner sans changement.
    """
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    emplacement = models.CharField(max_length=50, null=True, blank=True)
    ville = models.CharField(max_length=30)
    telephone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=70, null=True, blank=True)
    proprietaire = models.CharField(max_length=100, null=True, blank=True)
    quantiteNegative = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class TenantScopedModel(models.Model):
    """Base abstraite pour tout modèle métier appartenant à une Entreprise."""
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
