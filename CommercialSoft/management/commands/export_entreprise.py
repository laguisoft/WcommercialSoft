import json

from django.core.management.base import BaseCommand

from CommercialSoft.export_entreprise import construire_export, nom_fichier_export


class Command(BaseCommand):
    help = (
        "Exporte toutes les donnees de l'entreprise (base courante, branche main) "
        "vers un fichier JSON, pour import ulterieur dans une entreprise du Saas "
        "via 'import_entreprise'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default=None,
            help="Chemin du fichier de sortie (par defaut : export_entreprise_<date>.json)",
        )

    def handle(self, *args, **options):
        paquet = construire_export()
        chemin = options['output'] or nom_fichier_export(paquet)

        with open(chemin, 'w', encoding='utf-8') as fichier:
            json.dump(paquet, fichier, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Export ecrit dans {chemin}"))
        for modele, n in sorted(paquet['compteurs'].items()):
            self.stdout.write(f"  {modele} : {n}")
        self.stdout.write(f"Empreinte SHA256 : {paquet['empreinte_sha256']}")
