from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0023_alter_commande_typepayement'),
    ]

    operations = [
        migrations.AddField(
            model_name='commandeclient',
            name='motifRejet',
            field=models.TextField(blank=True, max_length=500, null=True),
        ),
    ]
