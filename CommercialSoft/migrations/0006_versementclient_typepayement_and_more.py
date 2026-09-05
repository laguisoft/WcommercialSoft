from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("CommercialSoft", "0005_client_boutique_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="versementclient",
            name="typePayement",
            field=models.CharField(
                choices=[
                    ("Espece", "Espece"),
                    ("Orange Money", "Orange Money"),
                    ("Banque", "Banque"),
                ],
                default="Espece",
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="versementfournisseur",
            name="typePayement",
            field=models.CharField(
                choices=[
                    ("Espece", "Espece"),
                    ("Orange Money", "Orange Money"),
                    ("Banque", "Banque"),
                ],
                default="Espece",
                max_length=15,
            ),
        ),
    ]
