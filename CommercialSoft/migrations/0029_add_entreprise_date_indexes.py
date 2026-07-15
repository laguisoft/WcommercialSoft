from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0028_entreprise_notnull_and_constraints'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='produit',
            index=models.Index(fields=['entreprise', 'datePeremption'], name='produit_entr_peremption_idx'),
        ),
        migrations.AddIndex(
            model_name='livraison',
            index=models.Index(fields=['entreprise', 'date'], name='livraison_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='commande',
            index=models.Index(fields=['entreprise', 'date'], name='commande_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='commandeproduit',
            index=models.Index(fields=['entreprise', 'date'], name='commandeproduit_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='commandeclient',
            index=models.Index(fields=['entreprise', 'date'], name='commandeclient_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='depense',
            index=models.Index(fields=['entreprise', 'date'], name='depense_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='decaissement',
            index=models.Index(fields=['entreprise', 'date'], name='decaissement_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='versementclient',
            index=models.Index(fields=['entreprise', 'date'], name='versementclient_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='pretclient',
            index=models.Index(fields=['entreprise', 'date'], name='pretclient_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='dettefournisseur',
            index=models.Index(fields=['entreprise', 'date'], name='dettefournisseur_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='versementfournisseur',
            index=models.Index(fields=['entreprise', 'date'], name='versementfourn_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='versementgerant',
            index=models.Index(fields=['entreprise', 'date'], name='versementgerant_entr_date_idx'),
        ),
        migrations.AddIndex(
            model_name='retour',
            index=models.Index(fields=['entreprise', 'date'], name='retour_entr_date_idx'),
        ),
    ]
