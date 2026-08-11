from django.contrib import admin

from .models import PaiementAbonnement


@admin.register(PaiementAbonnement)
class PaiementAbonnementAdmin(admin.ModelAdmin):
    list_display = (
        'merchant_reference', 'entreprise', 'duree_mois', 'montant',
        'statut', 'methode_paiement', 'date_creation',
    )
    list_filter = ('statut', 'entreprise')
    search_fields = ('merchant_reference', 'transaction_id', 'payer_number', 'entreprise__nom')
    readonly_fields = (
        'entreprise', 'duree_mois', 'montant', 'payer_number', 'merchant_reference',
        'transaction_id', 'statut', 'methode_paiement', 'reponse_brute',
        'date_creation', 'date_maj',
    )

    def has_add_permission(self, request):
        return False
