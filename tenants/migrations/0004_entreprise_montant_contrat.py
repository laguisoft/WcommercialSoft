from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_entreprise_date_fin_contrat"),
    ]

    operations = [
        migrations.AddField(
            model_name="entreprise",
            name="montant_contrat",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Montant annuel du contrat de cette entreprise, utilisé pour calculer le prix du renouvellement via Djomy.",
                verbose_name="Montant du contrat (annuel, GNF)",
            ),
        ),
    ]
