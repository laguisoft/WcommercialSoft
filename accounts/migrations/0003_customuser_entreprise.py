import django.db.models.deletion
from django.db import migrations, models


def backfill_entreprise(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    Entreprise = apps.get_model('tenants', 'Entreprise')
    default_entreprise = Entreprise.objects.first()
    if default_entreprise is None:
        return
    CustomUser.objects.filter(entreprise__isnull=True, is_superuser=False).update(entreprise=default_entreprise)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('accounts', '0002_remove_customuser_boutique'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='entreprise',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='utilisateurs', to='tenants.entreprise'),
        ),
        migrations.RunPython(backfill_entreprise, noop),
    ]
