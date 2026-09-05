import json

from django.core.management.base import BaseCommand, CommandError

from CommercialSoft.reparer_import_client_portail import analyser_reparation, executer_reparation
from tenants.models import Entreprise


class Command(BaseCommand):
    help = (
        "Repare les Client importes AVANT le correctif du lien vers leur compte "
        "portail (Client.user) : relie automatiquement ceux dont le compte Saas "
        "porte le meme nom d'utilisateur que dans l'ancien export (cas --creer "
        "de import_entreprise). Necessite le MEME fichier JSON que celui deja "
        "utilise pour import_entreprise sur cette entreprise."
    )

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Chemin du fichier JSON deja utilise pour import_entreprise")
        parser.add_argument('--entreprise', required=True, help="Nom exact de l'entreprise cible (tenants.Entreprise)")
        parser.add_argument('--dry-run', action='store_true', help="Affiche le rapport sans rien ecrire")
        parser.add_argument(
            '--lier', action='append', default=[], metavar='NOM_CLIENT:USERNAME_OU_ID_SAAS',
            help="Force le rattachement d'un client non resolu automatiquement "
                 "(ex: --lier \"Client X:jdupont\")",
        )

    def handle(self, *args, **options):
        try:
            entreprise = Entreprise.objects.get(nom=options['entreprise'])
        except Entreprise.DoesNotExist as exc:
            raise CommandError(f"Aucune entreprise nommee \"{options['entreprise']}\" dans Saas.") from exc

        with open(options['fichier'], encoding='utf-8') as fichier:
            paquet = json.load(fichier)

        rapport = analyser_reparation(paquet, entreprise)

        self.stdout.write(f"Deja relies (rien a faire) : {len(rapport['deja_lies'])}")
        self.stdout.write(self.style.SUCCESS(
            f"Resolus automatiquement (meme nom d'utilisateur) : {len(rapport['resolus'])}"
        ))
        for r in rapport['resolus']:
            self.stdout.write(f"  - {r['client']} -> {r['username']} (id={r['user_id']})")

        if rapport['introuvables']:
            self.stdout.write(self.style.WARNING(
                "Client introuvable cote Saas (nom different de l'export, ou pas encore importe) :"
            ))
            for nom in rapport['introuvables']:
                self.stdout.write(f"  - {nom}")

        if rapport['ambigus']:
            self.stdout.write(self.style.WARNING(
                "A relier manuellement avec --lier \"NOM_CLIENT:username_ou_id_saas\" :"
            ))
            for a in rapport['ambigus']:
                self.stdout.write(f"  - {a['client']} (ancien compte : {a['ancien_username']})")

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS("[DRY RUN] Rien n'a ete ecrit en base."))
            return

        overrides = {}
        for entree in options['lier']:
            try:
                nom_client, valeur = entree.split(':', 1)
            except ValueError as exc:
                raise CommandError(
                    f"Format invalide pour --lier : \"{entree}\" (attendu NOM_CLIENT:username_ou_id)"
                ) from exc
            overrides[nom_client] = valeur

        rapport_exec = executer_reparation(paquet, entreprise, overrides)
        self.stdout.write(self.style.SUCCESS(
            "Relies : " + (", ".join(rapport_exec['lies']) or "aucun")
        ))
        if rapport_exec['ignores']:
            self.stdout.write(self.style.WARNING(
                "Toujours non resolus : " + ", ".join(rapport_exec['ignores'])
            ))
