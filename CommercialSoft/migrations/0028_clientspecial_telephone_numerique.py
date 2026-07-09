import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0027_clientspecial_commande_clientspecial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientspecial',
            name='telephone',
            field=models.CharField(max_length=20, validators=[django.core.validators.RegexValidator('^\\d+$', 'Le telephone doit contenir uniquement des chiffres.')]),
        ),
    ]
