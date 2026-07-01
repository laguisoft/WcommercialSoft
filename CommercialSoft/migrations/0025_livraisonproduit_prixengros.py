from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0024_commandeclient_motifRejet'),
    ]

    operations = [
        migrations.AddField(
            model_name='livraisonproduit',
            name='prixEnGros',
            field=models.PositiveBigIntegerField(blank=True, default=0),
        ),
    ]
