import json
import os

from django.core.management.base import BaseCommand

from CommercialSoft.export_entreprise import (
    SEUIL_DECOUPAGE_MO_DEFAUT,
    construire_export,
    construire_exports_mensuels,
    nom_fichier_export,
    nom_fichier_export_lot,
    taille_octets,
)


class Command(BaseCommand):
    help = (
        "Exporte toutes les donnees de l'entreprise (base courante, branche main) "
        "vers un fichier JSON, pour import ulterieur dans une entreprise du Saas "
        "via 'import_entreprise'. Si l'export depasse --seuil-mo, bascule "
        "automatiquement sur plusieurs fichiers (un par mois de donnees "
        "historiques) pour eviter une erreur '413 Request Entity Too Large' a "
        "l'upload dans l'ecran d'import."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default=None,
            help="Chemin du fichier de sortie si l'export tient en un seul fichier "
                 "(par defaut : export_entreprise_<date>.json)",
        )
        parser.add_argument(
            '--dossier',
            default='.',
            help="Dossier de sortie des fichiers si l'export est decoupe (par defaut : dossier courant)",
        )
        parser.add_argument(
            '--seuil-mo',
            type=float,
            default=SEUIL_DECOUPAGE_MO_DEFAUT,
            help=f"Taille en Mo au-dela de laquelle decouper automatiquement l'export "
                 f"(par defaut : {SEUIL_DECOUPAGE_MO_DEFAUT})",
        )

    def handle(self, *args, **options):
        paquet = construire_export()
        taille = taille_octets(paquet)
        seuil_octets = options['seuil_mo'] * 1024 * 1024

        if taille <= seuil_octets:
            chemin = options['output'] or nom_fichier_export(paquet)
            with open(chemin, 'w', encoding='utf-8') as fichier:
                json.dump(paquet, fichier, ensure_ascii=False, indent=2)

            self.stdout.write(self.style.SUCCESS(
                f"Export ecrit dans {chemin} ({taille / 1024:.0f} Ko)"
            ))
            for modele, n in sorted(paquet['compteurs'].items()):
                self.stdout.write(f"  {modele} : {n}")
            self.stdout.write(f"Empreinte SHA256 : {paquet['empreinte_sha256']}")
            return

        self.stdout.write(self.style.WARNING(
            f"Export complet : {taille / 1024 / 1024:.1f} Mo (> {options['seuil_mo']:.0f} Mo) — "
            "decoupage automatique en plusieurs fichiers mensuels pour eviter une erreur "
            "413 a l'import."
        ))

        dossier = options['dossier']
        os.makedirs(dossier, exist_ok=True)
        paquets = construire_exports_mensuels()

        for lot in paquets:
            nom = nom_fichier_export_lot(lot)
            chemin = os.path.join(dossier, nom)
            with open(chemin, 'w', encoding='utf-8') as fichier:
                json.dump(lot, fichier, ensure_ascii=False, indent=2)

            taille_lot_ko = os.path.getsize(chemin) / 1024
            periode = lot.get('periode')
            periode_txt = f" ({periode['debut']} -> {periode['fin']})" if periode else ""
            self.stdout.write(
                f"  [{lot['lot']['index']}/{lot['lot']['total']}] {nom}{periode_txt} "
                f"- {taille_lot_ko:.0f} Ko"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(paquets)} fichiers generes dans '{dossier}'. A importer un par un dans "
            "Saas (menu Parametrage -> \"Importer les donnees d'un client (main)\"), dans "
            "n'importe quel ordre : chaque fichier contient sa propre copie des donnees de "
            "reference (produits, clients, ...), reutilisee sans doublon a chaque import."
        ))
