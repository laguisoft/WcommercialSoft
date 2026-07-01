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
        ('CommercialSoft', '0027_migrate_infoboutique_and_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name=modele,
            name='entreprise',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tenants.entreprise'),
        )
        for modele in MODELES
    ] + [
        migrations.AlterField(
            model_name='fournisseur',
            name='nom',
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='fournisseur',
            constraint=models.UniqueConstraint(fields=('entreprise', 'nom'), name='fournisseur_nom_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='categorie',
            name='nom',
            field=models.CharField(max_length=30),
        ),
        migrations.AddConstraint(
            model_name='categorie',
            constraint=models.UniqueConstraint(fields=('entreprise', 'nom'), name='categorie_nom_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='produit',
            name='codebare',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='produit',
            name='libelle',
            field=models.CharField(max_length=60),
        ),
        migrations.AddConstraint(
            model_name='produit',
            constraint=models.UniqueConstraint(fields=('entreprise', 'codebare'), name='produit_codebare_unique_par_entreprise'),
        ),
        migrations.AddConstraint(
            model_name='produit',
            constraint=models.UniqueConstraint(fields=('entreprise', 'libelle'), name='produit_libelle_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='societe',
            name='nom',
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='societe',
            constraint=models.UniqueConstraint(fields=('entreprise', 'nom'), name='societe_nom_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='client',
            name='nom',
            field=models.CharField(max_length=70),
        ),
        migrations.AddConstraint(
            model_name='client',
            constraint=models.UniqueConstraint(fields=('entreprise', 'nom'), name='client_nom_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='commande',
            name='client_uid',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name='commande',
            constraint=models.UniqueConstraint(fields=('entreprise', 'client_uid'), name='commande_client_uid_unique_par_entreprise'),
        ),
        migrations.AlterField(
            model_name='livraison',
            name='client_uid',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name='livraison',
            constraint=models.UniqueConstraint(fields=('entreprise', 'client_uid'), name='livraison_client_uid_unique_par_entreprise'),
        ),
        migrations.DeleteModel(
            name='InfoBoutique',
        ),
    ]
