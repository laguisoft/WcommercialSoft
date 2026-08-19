import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("CommercialSoft", "0021_client_user_commandeclient_commandeclientproduit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commande",
            name="date",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
    ]
