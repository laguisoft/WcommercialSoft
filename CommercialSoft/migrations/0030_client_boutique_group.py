from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_NAME = "Client Boutique"

PERMISSIONS = [
    ("CommercialSoft", "view_produit"),
    ("CommercialSoft", "add_commandeclient"),
    ("CommercialSoft", "view_commandeclient"),
    ("CommercialSoft", "view_commandeclientproduit"),
    ("CommercialSoft", "view_versementclient"),
    ("CommercialSoft", "view_pretclient"),
]


def create_group(apps, schema_editor):
    # Les permissions par defaut sont normalement creees par le signal
    # post_migrate, qui ne s'est pas encore declenche a ce stade lors d'un
    # "migrate" complet sur une base neuve : on les cree explicitement.
    app_config = apps.get_app_config("CommercialSoft")
    app_config.models_module = True
    create_permissions(app_config, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)

    permissions = Permission.objects.filter(
        content_type__app_label__in={app_label for app_label, _ in PERMISSIONS},
        codename__in={codename for _, codename in PERMISSIONS},
    )
    group.permissions.set(permissions)


def remove_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("CommercialSoft", "0029_merge_20260817_1824"),
    ]

    operations = [
        migrations.RunPython(create_group, remove_group),
    ]
