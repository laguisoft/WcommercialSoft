from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='entreprises_additionnelles',
            field=models.ManyToManyField(
                blank=True,
                help_text="Entreprises supplémentaires accessibles à cet utilisateur, en plus de son entreprise principale.",
                related_name='utilisateurs_additionnels',
                to='tenants.entreprise',
            ),
        ),
    ]
