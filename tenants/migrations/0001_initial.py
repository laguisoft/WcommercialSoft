from django.db import migrations, models


def create_default_entreprise(apps, schema_editor):
    Entreprise = apps.get_model('tenants', 'Entreprise')
    if not Entreprise.objects.exists():
        Entreprise.objects.create(
            nom="Entreprise par défaut",
            slug="entreprise-par-defaut",
            ville="",
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Entreprise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('actif', models.BooleanField(default=True)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('emplacement', models.CharField(blank=True, max_length=50, null=True)),
                ('ville', models.CharField(max_length=30)),
                ('telephone', models.CharField(blank=True, max_length=20, null=True)),
                ('email', models.EmailField(blank=True, max_length=70, null=True)),
                ('proprietaire', models.CharField(blank=True, max_length=100, null=True)),
                ('quantiteNegative', models.BooleanField(default=True)),
            ],
        ),
        migrations.RunPython(create_default_entreprise, noop),
    ]
