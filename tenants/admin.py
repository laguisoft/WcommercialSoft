from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .backup import construire_sauvegarde, sauvegarder_sur_disque
from .models import Entreprise


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'actif', 'ville', 'date_creation', 'date_fin_contrat', 'suppression_securisee')
    search_fields = ('nom', 'ville')
    list_filter = ('actif',)
    date_hierarchy = 'date_fin_contrat'
    prepopulated_fields = {'slug': ('nom',)}

    def suppression_securisee(self, obj):
        return format_html(
            '<a href="{}">Supprimer (avec sauvegarde)</a>',
            reverse('supprimer_entreprise', args=[obj.pk]),
        )
    suppression_securisee.short_description = "Suppression"

    def _sauvegarder_avant_suppression(self, request, entreprise):
        """La suppression d'une Entreprise entraine, en cascade, la perte de
        toutes ses donnees metier (TenantScopedModel). On sauvegarde donc
        systematiquement sur disque avant de laisser Django proceder,
        peu importe le chemin de suppression emprunte (objet unique ou
        suppression groupee)."""
        paquet = construire_sauvegarde(entreprise)
        chemin = sauvegarder_sur_disque(paquet, entreprise)
        self.message_user(
            request,
            f"Sauvegarde de \"{entreprise.nom}\" ecrite avant suppression : {chemin}",
            level=messages.WARNING,
        )

    def delete_model(self, request, obj):
        self._sauvegarder_avant_suppression(request, obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for entreprise in queryset:
            self._sauvegarder_avant_suppression(request, entreprise)
        super().delete_queryset(request, queryset)
