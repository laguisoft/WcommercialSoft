from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0025_livraisonproduit_prixengros'),
    ]

    operations = [
        migrations.AddField(
            model_name='produit',
            name='special',
            field=models.BooleanField(default=False, verbose_name='Produit special (infos client requises a la vente)'),
        ),
        migrations.AddField(
            model_name='client',
            name='prenom',
            field=models.CharField(blank=True, max_length=70, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='clientSpecial',
            field=models.BooleanField(default=False, verbose_name='Client special (achat de produit special)'),
        ),
    ]
