from django.contrib import admin

from .models import Entreprise


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'actif', 'ville', 'date_creation', 'date_fin_contrat')
    search_fields = ('nom', 'ville')
    list_filter = ('actif',)
    date_hierarchy = 'date_fin_contrat'
    prepopulated_fields = {'slug': ('nom',)}
