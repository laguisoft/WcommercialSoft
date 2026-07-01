from django.contrib import admin

from .models import Entreprise


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'actif', 'ville', 'date_creation')
    search_fields = ('nom', 'ville')
    list_filter = ('actif',)
    prepopulated_fields = {'slug': ('nom',)}
