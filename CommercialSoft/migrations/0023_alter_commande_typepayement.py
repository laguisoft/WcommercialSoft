from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("CommercialSoft", "0022_commande_date_datetimefield"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commande",
            name="typePayement",
            field=models.CharField(
                choices=[
                    ("Espece", "Espece"),
                    ("Pret", "Pret"),
                    ("Don", "Don"),
                    ("Orange Money", "Orange Money"),
                ],
                default="Espece",
                max_length=20,
            ),
        ),
    ]
