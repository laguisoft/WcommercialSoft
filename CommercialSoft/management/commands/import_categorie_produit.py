import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from CommercialSoft.models import Categorie, Produit
from tenants.models import Entreprise


class Command(BaseCommand):
    help = (
        "Importe les categories et produits exportes depuis la branche main "
        "(fixture JSON produite par 'manage.py dumpdata CommercialSoft.categorie "
        "CommercialSoft.produit') vers une entreprise de Saas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'fixture',
            help="Chemin du fichier JSON produit par dumpdata sur la branche main",
        )
        parser.add_argument(
            '--entreprise',
            required=True,
            help="Nom exact de l'entreprise cible (colonne 'nom' de tenants.Entreprise)",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Simule l'import et affiche le resume sans rien ecrire en base",
        )

    def handle(self, *args, **options):
        try:
            entreprise = Entreprise.objects.get(nom=options['entreprise'])
        except Entreprise.DoesNotExist as exc:
            raise CommandError(
                f"Aucune entreprise nommee \"{options['entreprise']}\" dans Saas."
            ) from exc

        with open(options['fixture'], encoding='utf-8') as fichier:
            objets = json.load(fichier)

        categories_src = [o for o in objets if o['model'].lower() == 'commercialsoft.categorie']
        produits_src = [o for o in objets if o['model'].lower() == 'commercialsoft.produit']

        if not categories_src and not produits_src:
            raise CommandError(
                "Aucun objet CommercialSoft.categorie / CommercialSoft.produit trouve dans "
                f"{options['fixture']}."
            )

        dry_run = options['dry_run']
        categorie_par_ancien_pk = {}
        categories_creees = 0
        categories_reutilisees = 0
        produits_crees = 0
        produits_ignores = 0

        with transaction.atomic():
            for obj in categories_src:
                nom = obj['fields']['nom']
                categorie, cree = Categorie.objects.get_or_create(entreprise=entreprise, nom=nom)
                categorie_par_ancien_pk[obj['pk']] = categorie
                if cree:
                    categories_creees += 1
                else:
                    categories_reutilisees += 1

            for obj in produits_src:
                fields = obj['fields']
                libelle = fields['libelle']

                if Produit.objects.filter(entreprise=entreprise, libelle=libelle).exists():
                    produits_ignores += 1
                    self.stdout.write(self.style.WARNING(
                        f"Ignore (libelle deja present pour cette entreprise) : {libelle}"
                    ))
                    continue

                codebare = fields.get('codebare') or None
                if codebare and Produit.objects.filter(entreprise=entreprise, codebare=codebare).exists():
                    self.stdout.write(self.style.WARNING(
                        f"Code-barre \"{codebare}\" deja utilise pour cette entreprise, "
                        f"laisse vide pour : {libelle}"
                    ))
                    codebare = None

                ancienne_categorie_pk = fields.get('categorie')
                categorie = categorie_par_ancien_pk.get(ancienne_categorie_pk) if ancienne_categorie_pk else None

                Produit.objects.create(
                    entreprise=entreprise,
                    codebare=codebare,
                    categorie=categorie,
                    libelle=libelle,
                    quantite=fields['quantite'],
                    prixAchat=fields['prixAchat'],
                    prixEnGros=fields['prixEnGros'],
                    prixDetail=fields['prixDetail'],
                    autrePrix=fields.get('autrePrix', 0),
                    date=fields['date'],
                    datePeremption=fields['datePeremption'],
                    seuil=fields.get('seuil', 0),
                    commentaire=fields.get('commentaire'),
                    quantiteTotal=fields.get('quantiteTotal', 0),
                )
                produits_crees += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Categories : {categories_creees} creees, {categories_reutilisees} deja existantes.\n"
            f"Produits : {produits_crees} crees, {produits_ignores} ignores "
            f"(libelle deja present pour \"{entreprise.nom}\")."
            + (" [DRY RUN, rien n'a ete ecrit en base]" if dry_run else "")
        ))
