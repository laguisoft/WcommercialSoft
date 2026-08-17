import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from CommercialSoft.import_entreprise import analyser, executer, extraire_utilisateurs
from tenants.models import Entreprise


class Command(BaseCommand):
    help = (
        "Importe un paquet exporte depuis la branche main (manage.py export_entreprise) "
        "vers une entreprise du Saas. Pour chaque utilisateur historique du fichier, "
        "un mapping explicite est requis : --lier ancien_username:id_utilisateur_saas "
        "pour le rattacher a un compte existant, ou --creer ancien_username pour lui "
        "creer un nouveau compte (mot de passe temporaire genere)."
    )

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Chemin du fichier JSON produit par export_entreprise sur main")
        parser.add_argument('--entreprise', required=True, help="Nom exact de l'entreprise cible (tenants.Entreprise)")
        parser.add_argument('--dry-run', action='store_true', help="Simule et affiche le rapport sans rien ecrire")
        parser.add_argument(
            '--lier', action='append', default=[], metavar='ANCIEN_USERNAME:ID_UTILISATEUR_SAAS',
            help="Rattache l'utilisateur historique ANCIEN_USERNAME au compte Saas existant d'id donne",
        )
        parser.add_argument(
            '--creer', action='append', default=[], metavar='ANCIEN_USERNAME',
            help="Cree un nouveau compte Saas pour l'utilisateur historique ANCIEN_USERNAME",
        )

    def handle(self, *args, **options):
        try:
            entreprise = Entreprise.objects.get(nom=options['entreprise'])
        except Entreprise.DoesNotExist as exc:
            raise CommandError(f"Aucune entreprise nommee \"{options['entreprise']}\" dans Saas.") from exc

        with open(options['fichier'], encoding='utf-8') as fichier:
            paquet = json.load(fichier)

        utilisateurs = extraire_utilisateurs(paquet)
        par_username = {u['fields']['username']: u['pk'] for u in utilisateurs}

        mapping = {}
        for entree in options['lier']:
            try:
                username, id_utilisateur = entree.split(':', 1)
            except ValueError as exc:
                raise CommandError(f"Format invalide pour --lier : \"{entree}\" (attendu ANCIEN_USERNAME:ID)") from exc
            if username not in par_username:
                raise CommandError(f"Utilisateur historique inconnu dans le fichier : \"{username}\"")
            mapping[par_username[username]] = {'action': 'lier', 'user_id': int(id_utilisateur)}

        for username in options['creer']:
            if username not in par_username:
                raise CommandError(f"Utilisateur historique inconnu dans le fichier : \"{username}\"")
            mapping[par_username[username]] = {'action': 'creer'}

        manquants = set(par_username) - {u['fields']['username'] for u in utilisateurs if u['pk'] in mapping}
        if manquants:
            raise CommandError(
                "Mapping manquant pour : " + ", ".join(sorted(manquants)) +
                " (utiliser --lier ou --creer pour chacun)"
            )

        rapport_analyse = analyser(paquet, entreprise)
        if rapport_analyse['deja_importe'] and not options['dry_run']:
            raise CommandError(
                "Cet export a deja ete importe pour cette entreprise (meme empreinte). "
                "Relancer avec un nouvel export si c'est intentionnel."
            )

        self.stdout.write("Comptages du fichier :")
        for modele, n in sorted(rapport_analyse['a_creer'].items()):
            self.stdout.write(f"  {modele} : {n}")
        for conflit in rapport_analyse['conflits']:
            self.stdout.write(self.style.WARNING(conflit))

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS("[DRY RUN] Rien n'a ete ecrit en base."))
            return

        User = get_user_model()
        importe_par = User.objects.filter(is_superuser=True).first()
        rapport = executer(paquet, entreprise, mapping, importe_par)

        self.stdout.write(self.style.SUCCESS(f"Import termine pour \"{entreprise.nom}\"."))
        self.stdout.write("Crees : " + json.dumps(rapport['crees'], ensure_ascii=False))
        self.stdout.write("Reutilises : " + json.dumps(rapport['reutilises'], ensure_ascii=False))
        if rapport['ignores']:
            self.stdout.write(self.style.WARNING("Ignores (reference manquante) : " + json.dumps(rapport['ignores'], ensure_ascii=False)))
        if rapport['comptes_crees']:
            self.stdout.write(self.style.WARNING(
                "Nouveaux comptes crees (mots de passe temporaires a communiquer) : " +
                ", ".join(rapport['comptes_crees'])
            ))
