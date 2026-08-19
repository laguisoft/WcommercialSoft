import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CommercialSoft', '0026_produit_special'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientSpecial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=70)),
                ('prenom', models.CharField(blank=True, max_length=70, null=True)),
                ('telephone', models.CharField(max_length=20)),
            ],
        ),
        migrations.AddField(
            model_name='commande',
            name='clientSpecial',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='achats', to='CommercialSoft.clientspecial'),
        ),
    ]
