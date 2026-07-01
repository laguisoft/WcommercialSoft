import django.db.models.deletion
from django.db import migrations, models

MODELES = [
    'fournisseur',
    'categorie',
    'produit',
    'livraison',
    'livraisonproduit',
    'societe',
    'client',
    'commande',
    'commandeproduit',
    'commandeclient',
    'commandeclientproduit',
    'categorie_depense',
    'depense',
    'categorie_decaissement',
    'decaissement',
    'versementclient',
    'pretclient',
    'dettefournisseur',
    'versementfournisseur',
    'versementgerant',
    'retour',
]


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('CommercialSoft', '0025_livraisonproduit_prixengros'),
    ]

    operations = [
        migrations.AddField(
            model_name=modele,
            name='entreprise',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='tenants.entreprise'),
        )
        for modele in MODELES
    ]
