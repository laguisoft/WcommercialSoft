from django.db import models

from tenants.models import TenantScopedModel

# Statuts renvoyés par l'API Djomy (create_payment_gateway / verify_payment).
STATUT_CHOICES = [
    ('CREATED', 'Créé'),
    ('PENDING', 'En attente'),
    ('REDIRECTED', 'Redirigé vers le portail Djomy'),
    ('SUCCESS', 'Payé'),
    ('FAILED', 'Échoué'),
    ('CANCELLED', 'Annulé'),
    ('TIMEOUT', 'Expiré'),
    ('REFUNDED', 'Remboursé'),
]


class PaiementAbonnement(TenantScopedModel):
    """Trace une tentative de paiement Djomy pour le renouvellement d'abonnement d'une entreprise."""

    duree_mois = models.PositiveSmallIntegerField(verbose_name="Durée (mois)")
    montant = models.PositiveIntegerField(verbose_name="Montant (GNF)")
    payer_number = models.CharField(max_length=20, verbose_name="Numéro du payeur")
    merchant_reference = models.CharField(max_length=64, unique=True)
    transaction_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='CREATED')
    methode_paiement = models.CharField(max_length=30, null=True, blank=True)
    reponse_brute = models.JSONField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.merchant_reference} ({self.statut})"

    @property
    def est_payee(self):
        return self.statut == 'SUCCESS'

    @property
    def en_cours(self):
        return self.statut in ('CREATED', 'PENDING', 'REDIRECTED')
