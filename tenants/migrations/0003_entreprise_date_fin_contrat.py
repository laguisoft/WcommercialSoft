from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_entreprise_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="entreprise",
            name="date_fin_contrat",
            field=models.DateField(blank=True, null=True, verbose_name="Fin du contrat"),
        ),
    ]
