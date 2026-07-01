from django.db import migrations

MODELES = [
    'Fournisseur',
    'Categorie',
    'Produit',
    'Livraison',
    'LivraisonProduit',
    'Societe',
    'Client',
    'Commande',
    'CommandeProduit',
    'CommandeClient',
    'CommandeClientProduit',
    'Categorie_Depense',
    'Depense',
    'Categorie_Decaissement',
    'Decaissement',
    'VersementClient',
    'PretClient',
    'DetteFournisseur',
    'VersementFournisseur',
    'VersementGerant',
    'Retour',
]


def migrate_infoboutique_and_backfill(apps, schema_editor):
    Entreprise = apps.get_model('tenants', 'Entreprise')
    InfoBoutique = apps.get_model('CommercialSoft', 'InfoBoutique')

    default_entreprise = Entreprise.objects.first()
    if default_entreprise is None:
        default_entreprise = Entreprise.objects.create(
            nom="Entreprise par défaut", slug="entreprise-par-defaut", ville="",
        )

    boutique = InfoBoutique.objects.first()
    if boutique is not None:
        default_entreprise.nom = boutique.nom
        default_entreprise.emplacement = boutique.emplacement
        default_entreprise.ville = boutique.ville
        default_entreprise.telephone = boutique.telephone
        default_entreprise.email = boutique.email
        default_entreprise.proprietaire = boutique.proprietaire
        default_entreprise.quantiteNegative = boutique.quantiteNegative
        default_entreprise.save()

    for nom_modele in MODELES:
        Modele = apps.get_model('CommercialSoft', nom_modele)
        Modele.objects.filter(entreprise__isnull=True).update(entreprise=default_entreprise)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0026_add_entreprise_nullable'),
    ]

    operations = [
        migrations.RunPython(migrate_infoboutique_and_backfill, noop),
    ]
