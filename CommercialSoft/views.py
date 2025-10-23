import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from .forms import *
from .models import *
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.timezone import now, localdate
from django.db import IntegrityError
from django.http import JsonResponse
from django.db import transaction
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Sum, F, ExpressionWrapper, IntegerField, DecimalField
from django.contrib.auth import get_user_model
import json
User = get_user_model()

# Create your views here.

#------------------------ Gestion des droits d'acces avec les decorateur -----------------
def est_administrateur(user):
    return user.groups.filter(name='Administrateur').exists()

def est_gestionnaire(user):
    return user.groups.filter(name='Gestionnaire').exists()

def est_utilisateur(user):
    return user.groups.filter(name='Utilisateur').exists()

def est_comptable(user):
    return user.groups.filter(name='Comptable').exists()


#separateur de milieu
def separateur(valeur):
    return f"{valeur:,}".replace(",", " ")




# Create your views here.

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                
                request.session['user_connect'] = request.user
                messages.success(request, 'Connexion réussie.')
                return redirect('commerce_dashboard')  # Remplacez 'home' par le nom de votre page d'accueil
            else:
                messages.error(request, 'utilisateur ou mot de passe incorrect')
        else:
            messages.error(request, 'Veuillez remplir le formulaire correctement.')
    else:
        form = LoginForm()
    return render(request, 'CommercialSoft/login.html', {'form': form})





@login_required
def dashboard(request):
    info_boutique = InfoBoutique.objects.first()
    total_produits = Produit.objects.count()
    produits_perimes = Produit.objects.filter(datePeremption__lt=now()).count()
    produits_rupture = Produit.objects.filter(quantite__lte=F('seuil')).count()
    total_dettes = PretClient.objects.count()

    context = {
        'nom_agent': request.user.username,
        'numero_user': request.user.id,
        'boutique': info_boutique,
        'total_produits': total_produits,
        'produits_perimes': produits_perimes,
        'produits_rupture': produits_rupture,
        'total_dettes': total_dettes,
    }

    return render(request, 'CommercialSoft/dashboard.html', context)









# examen Views
@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def fournisseur_list_create(request):
    if request.method == "POST":
        form = FournisseurForm(request.POST)
        if form.is_valid():
            four = form.save(commit=False)
            four.date = timezone.now().date()
            four.save()  # Sauvegarder après modification
            messages.success(request, "Fournisseur créée avec succès !")
            return redirect('commerce_fournisseur')
        else:
            messages.error(request, "Erreur lors de la création du fournisseur.")
    else:
        form = FournisseurForm()
    
    fournisseur = Fournisseur.objects.all()
    paginator = Paginator(fournisseur, 15)
    page = request.GET.get('page')
    paginated = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/fournisseur.html', {'form': form,'listes': paginated})



@login_required
def fournisseur_edit(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == "POST":
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, "Fournisseur mise à jour avec succès!")
            return redirect('commerce_fournisseur')
        else:
            messages.error(request, "Erreur lors de la mise à jour du fournisseur.")
    else:
        form = FournisseurForm(instance=fournisseur)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def fournisseur_delete(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    try:
        fournisseur.delete()
        messages.success(request, "Fournisseur supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce fournisseur est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_fournisseur')





 # Example for Patient Views
@user_passes_test(est_administrateur)
@login_required
def situation_fournisseur(request):
    fournisseur=FournisseurForm()
    liste=Fournisseur.objects.all()
    return render(request, 'CommercialSoft/situationFournisseur.html',{'form':fournisseur,'listes':liste})






@login_required
def recherche_fournisseur(request):
    if request.method == "POST":
        numero = request.POST.get('idFournisseur', '0').strip()  # Récupérer le numéro envoyé
        numero=int(numero)
        fournisseurs = Fournisseur.objects.filter(id=numero) if numero else Fournisseur.objects.all()
        
        print(f"Valeur de numero : '{numero}'")  # Debugging
        # Construire une réponse JSON
        fournisseurs_data = [
            {
                "id": fournisseur.id,
                "nom": fournisseur.nom,
                "telephone": fournisseur.telephone,
                "adresse": fournisseur.adresse,
                "total_pret": fournisseur.detteFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0,
                "total_versement": fournisseur.versementFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0,
                "balance": (fournisseur.detteFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0) - 
                           (fournisseur.versementFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0),
            }
            for fournisseur in fournisseurs
        ]

        
        return JsonResponse({"fournisseurs": fournisseurs_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)







# Views
@login_required
def categorie_list_create(request):
    if request.method == "POST":
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Categorie créée avec succès !")
            return redirect('commerce_categorie')
        else:
            messages.error(request, "Erreur lors de la création de la categorie.")
    else:
        form = CategorieForm()
    
    categorie = Categorie.objects.all()
    paginator = Paginator(categorie, 15)
    page = request.GET.get('page')
    paginated = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/categorie.html', {'form': form,'listes': paginated})



@login_required
def categorie_edit(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == "POST":
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, "Categorie mise à jour avec succès!")
            return redirect('commerce_categorie')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la categorie.")
    else:
        form = CategorieForm(instance=categorie)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@login_required
def categorie_delete(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    try:
        categorie.delete()
        messages.success(request, "Categorie supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette categorie est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_categorie')


# examen Views
@login_required
def produit_list_create(request):
    if request.method == "POST":
        form = ProduitForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Produit créée avec succès !")
            return redirect('commerce_produit')
        else:
            messages.error(request, "Erreur lors de la création de la produit.")
    else:
        form = ProduitForm()
    
    produit = Produit.objects.all().order_by('id')
    paginator = Paginator(produit, 15)
    page = request.GET.get('page')
    paginated = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/produit.html', {'form': form,'listes': paginated})




 # Example for Patient Views
@login_required
def produit_list(request):
    categorie=Categorie.objects.all()
    produit=Produit.objects.all()
    return render(request, 'CommercialSoft/listeProduits.html', {'categories':categorie,'produits':produit})




 # Example for Patient Views
@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def inventaire(request):
    categorie=Categorie.objects.all()
    produit=Produit.objects.all()
    return render(request, 'CommercialSoft/inventaire.html',{'listesCat':categorie,'listes':produit})





@login_required
def produit_perime(request):
    aujourdhui = timezone.now().date()
    produits_perimes = Produit.objects.filter(datePeremption__lt=aujourdhui)
    return render(request, 'CommercialSoft/produitPerime.html',{'listes':produits_perimes})




@login_required
def produit_rupture(request):
    produits_rupture=Produit.objects.filter(quantite__lte=F('seuil'))
    return render(request, 'CommercialSoft/produitEnRupture.html',{'listes':produits_rupture})



@login_required
def produit_livrer(request):
    return render(request, 'CommercialSoft/produitLivrer.html')



@login_required
def produit_vendu(request):
    users = User.objects.all()  # Récupérer tous les utilisateurs
    return render(request, 'CommercialSoft/produitVendu.html', {'users': users})



@login_required
def vente_par_client(request):
    client = Client.objects.all()  # Récupérer tous les utilisateurs
    return render(request, 'CommercialSoft/venteParClient.html', {'clients': client})


@login_required
def vente_par_payement(request):
    return render(request, 'CommercialSoft/venteParPayement.html')




@login_required
def vente_par_type(request):
    return render(request, 'CommercialSoft/venteParTypeVente.html')



@login_required
def detail_vente(request):
    users = User.objects.all()  # Récupérer tous les utilisateurs
    return render(request, 'CommercialSoft/detailVente.html', {'users': users})



@login_required
def situation_vente(request):
    produit = Produit.objects.all()  # Récupérer tous les utilisateurs
    return render(request, 'CommercialSoft/situationVente.html', {'listes': produit})






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def reception_create(request):
    if request.method == 'POST':
        livraison_form = LivraisonForm(request.POST)

        # ✅ 1) COPIE du POST modifiable
        post_data = request.POST.copy()

        # ✅ 2) Récupérer le nombre total de formulaires dans le formset
        total_forms = int(post_data.get('livraisonproduit_set-TOTAL_FORMS', 0))

        # ✅ 3) Boucle sur chaque formulaire du formset
        for i in range(total_forms):
            key = f"livraisonproduit_set-{i}-peremption"
            val = post_data.get(key, "").strip()

            if val:
                try:
                    # ✅ Séparer MM/AA
                    mm, yy = val.split("/")

                    # ✅ Transformer AA en YYYY (ex: 25 -> 2025)
                    yy = "20" + yy  # Si tu veux une logique intelligente 19xx/20xx, je peux te l'ajouter

                    # ✅ Reformater en YYYY-MM-01 (format accepté par DateField)
                    post_data[key] = f"{yy}-{mm}-01"
                except:
                    # si mauvais format, on laisse Django déclencher l'erreur
                    pass

        # ✅ 4) On recrée le formset AVEC les valeurs corrigées
        formset = LivraisonProduitFormSet(post_data)

        # ✅ 5) Validation
        if livraison_form.is_valid() and formset.is_valid():
            with transaction.atomic():  # évite les données partielles
                try:
                    # ✅ Enregistrer la livraison
                    livraison = livraison_form.save()

                    # ✅ Traiter chaque ligne du formset
                    for form in formset:
                        if not (form.cleaned_data.get('produit') and form.cleaned_data.get('quantite')):
                            continue  # ignorer les lignes vides

                        livraison_produit = form.save(commit=False)
                        livraison_produit.livraison = livraison

                        # ✅ Mise à jour du stock produit
                        produit_id=livraison_produit.produit.id
                        # produit livraison_produit.produit
                        produit = Produit.objects.get(id=produit_id)
                        produit.quantiteTotal += livraison_produit.quantite
                        produit.prixAchat = livraison_produit.prix
                        produit.quantite += livraison_produit.quantite
                        produit.prixDetail = livraison_produit.prixDetail
                        produit.save()

                        # ✅ Enregistrer la ligne de livraison
                        livraison_produit.save()

                    messages.success(request, "Enregistrement réussi")
                    return redirect('commerce_reception')

                except Exception as e:
                    messages.error(request, f"Erreur lors de l’enregistrement : {e}")

        else:
            # Afficher les erreurs
            messages.error(request, "Formulaire invalide")
            for error in formset.errors:
                if error:
                    messages.error(request, f"Erreur dans un formulaire : {error}")

    # ✅ 6) GET → afficher page avec formulaires vides
    livraison_form = LivraisonForm()
    formset = LivraisonProduitFormSet()
    produits = Produit.objects.all()

    return render(request, 'CommercialSoft/reception2.html', {
        'livraison_form': livraison_form,
        'formset': formset,
        'listes': produits,
    })










#------------------------- nouvelle reception ------------------------------
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import date
import json

from .models import Produit, Fournisseur, Livraison, LivraisonProduit, DetteFournisseur

@login_required
@require_GET
def api_reception(request):
    """
    Données de base pour le offline :
    - produits (partagés avec la vente via localforage 'produits')
    - fournisseurs (localforage 'fournisseurs')
    """
    prods = list(Produit.objects.values(
        "id", "libelle", "prixAchat", "prixDetail", "prixEnGros", "quantite"
    ))
    fours = list(Fournisseur.objects.values("id", "nom"))
    return JsonResponse({"produits": prods, "fournisseurs": fours})


def _mm_aa_to_date(mm_aa: str):
    """ '10/25' -> date(2025,10,1). Retourne None si vide/KO. """
    try:
        mm, aa = (mm_aa or "").split("/")
        yy = int("20" + aa.strip())
        mm = max(1, min(int(mm.strip()), 12))
        return date(yy, mm, 1)
    except Exception:
        return None


@csrf_exempt
@require_POST
@login_required
def api_sync_livraisons(request):
    """
    Reçoit UNE livraison locale (offline) et la persiste.
    - crée Livraison + LivraisonProduit
    - met à jour le stock Produit (entrée)
    - enregistre DetteFournisseur si typePayement == 'Pret'
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"success": False, "error": f"JSON invalide: {e}"}, status=400)

    fournisseur_id = payload.get("fournisseur")
    lignes = payload.get("lignes", [])
    montant = int(payload.get("montant") or 0)
    numeroFacture = payload.get("numeroFacture") or None
    typePayement = payload.get("typePayement") or "Espece"
    date_str = payload.get("date") or ""

    if not fournisseur_id or not lignes:
        return JsonResponse({"success": False, "error": "Fournisseur et lignes requis"}, status=400)

    try:
        fournisseur = Fournisseur.objects.get(id=fournisseur_id)
    except Fournisseur.DoesNotExist:
        return JsonResponse({"success": False, "error": "Fournisseur introuvable"}, status=404)

    liv_date = parse_date(date_str) or date.today()

    try:
        with transaction.atomic():
            liv = Livraison.objects.create(
                fournisseur=fournisseur,
                date=liv_date,
                montant=montant,
                numeroFacture=numeroFacture,
                typePayement=typePayement,
            )

            for li in lignes:
                pid = li.get("produit_id")
                qte = int(li.get("quantite") or 0)
                prix = int(float(li.get("prix") or 0))
                prixDetail = int(float(li.get("prixDetail") or 0))
                per_mm_aa = (li.get("peremption") or "").strip()
                if not pid or qte <= 0 or prix <= 0:
                    continue

                pr = Produit.objects.filter(id=pid).first()
                if not pr:
                    continue

                per_date = _mm_aa_to_date(per_mm_aa)

                LivraisonProduit.objects.create(
                    livraison=liv,
                    produit=pr,
                    quantite=qte,
                    prix=prix,
                    prixDetail=prixDetail,
                    peremption=per_date
                )

                # entrée de stock + mise à jour prix
                pr.quantite += qte
                pr.quantiteTotal += qte
                pr.prixAchat = prix
                if prixDetail > 0:
                    pr.prixDetail = prixDetail
                pr.save()

            if typePayement == "Pret":
                DetteFournisseur.objects.create(
                    fournisseur=fournisseur,
                    montant=montant,
                    date=liv_date,
                    facture=liv
                )

        return JsonResponse({"success": True, "livraison_id": liv.id})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)








"""
@login_required
def reception_create(request):
    if request.method == 'POST':
        livraison_form = LivraisonForm(request.POST)
        detteFournisseur_form = DetteFournisseur(request.POST)
        produits_json = request.POST.get('jsonDataInput', '[]')  # JSON envoyé depuis JS
        try:
            produits_data = json.loads(produits_json)
        except json.JSONDecodeError:
            produits_data = []

        if livraison_form.is_valid() and (not produits_data == []):
            with transaction.atomic():
                try:
                    # Création de la commande
                    livraison= livraison_form.save()

                    montantTotal = 0

                    for item in produits_data:
                        produit_id = item.get('id')
                        quantite = int(item.get('quantite', 0))
                        prix = int(item.get('prix', 0))
                        prixDetail=int(item.get('prixDetail',0))
                        peremption=date(item.get('peremption'))

                        if not produit_id or quantite <= 0:
                            continue

                        produit = Produit.objects.get(id=produit_id)

                        produit.quantite += quantite
                        produit.save()

                        LivraisonProduit.objects.create(
                            livraison=livraison,
                            produit=produit,
                            quantite=quantite,
                            prix=prix,
                            prixDetail=prixDetail,
                            peremption=peremption
                        )

                        montantTotal += prix * quantite

                    livraison.montant = montantTotal
                    livraison.save()

                    # Gestion Pret
                    if livraison.typePayement == "Pret":
                        detteFournisseur_form.fields['fournisseur'].required = True
                        if detteFournisseur_form.is_valid():
                            pret = detteFournisseur_form.save(commit=False)
                            pret.livraison = livraison
                            pret.montant = livraison.montant
                            pret.date = livraison.date
                            pret.save()
                            livraison.fournisseur = pret.fournisseur
                            livraison.save()
                        else:
                            messages.error(request, "Erreur dans le formulaire de Pret.")
                    else:
                        detteFournisseur_form.fields['fournisseur'].required = False

                    messages.success(request, "Enregistrement réussi !")

                    # Préparer les formulaires vides pour réaffichage
                    livraison_form = LivraisonForm()
                    detteFournisseur_form = DetteFournisseurForm()
                    produits = Produit.objects.all()
                    return render(request, 'CommercialSoft/reception2.html', {
                        'commande_form': livraison_form,
                        'pret_form': pret_form,
                        'listes': produits,
                        'recu_url': '/commerce_recu',
                        'venteId': livraison.id
                    })
                except Exception as e:
                    messages.error(request, f"Erreur d'enregistrement: {e}")
        else:
            messages.error(request, "Formulaire incomplet ou aucun produit sélectionné.")

    # GET ou formulaire invalide
    livraison_form = LivraisonForm()
    detteFournisseur_form = DetteFournisseurForm()
    produits = Produit.objects.all()
    boutique= InfoBoutique.objects.first()
    return render(request, 'CommercialSoft/reception2.html', {
        'commande_form': livraison_form,
        'pret_form': detteFournisseur_form,
        'listes': produits,
        'user':request.user,
        'boutique': boutique,
    })
"""






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def reception_delete(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    try:
        livraison.delete()
        messages.success(request, "livraison supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette livraison est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('produitLivrer')




@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def reception_edit(request, pk):
    livraisonP = get_object_or_404(LivraisonProduit, pk=pk)
    if request.method == "POST":
        form = LivraisonProduitForm(request.POST, instance=livraisonP)
        if form.is_valid():
            livraisonP.save()
            messages.success(request, "Livraison mise à jour avec succès!")
            return redirect('produitLivrer')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la livraison.")
    else:
        form = LivraisonProduitForm(instance=livraisonP)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})




@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def detail_reception(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)

    if request.method == "POST":
        form = LivraisonProduitForm(request.POST)
        if form.is_valid():  # Vérifier la validité AVANT d'utiliser form
            produit = form.save(commit=False)
            produit.livraison = livraison
            produit.save()
            return redirect('commerce_detailReception', pk=pk)  # Rediriger après un POST réussi

    else:
        form = LivraisonProduitForm()  # Instancier un nouveau formulaire

    produits = LivraisonProduit.objects.filter(livraison=livraison)
    return render(request, 'CommercialSoft/detailProduitLivrer.html', {'listes': produits, 'form': form,'livraison': livraison})





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def produit_livrer_delete(request, pk):
    livraisonP = get_object_or_404(LivraisonProduit, pk=pk)
    try:
        livraisonP.delete()
        messages.success(request, "Produit supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette produit est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_detailReception', livraisonP.livraison.id)



@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def reception_par_produit(request):
    produit = Produit.objects.all()  # Récupérer tous les utilisateurs
    fournisseur=Fournisseur.objects.all()
    return render(request, 'CommercialSoft/receptionParProduit.html', {'listes': produit,'listesFour':fournisseur})




@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def recherche_reception_produit(request):
    if request.method == "POST":
        idFournisseur = request.POST.get('idFournisseur')
        idProduit = request.POST.get('idProduit')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Préparation de la requête avec select_related pour optimiser
        livraisons_produits = LivraisonProduit.objects.select_related('livraison', 'produit', 'livraison__fournisseur')

        # Application des filtres si fournis
        if dateDebut:
            livraisons_produits = livraisons_produits.filter(livraison__date__gte=dateDebut)
        if dateFin:
            livraisons_produits = livraisons_produits.filter(livraison__date__lte=dateFin)
        if idFournisseur:
            livraisons_produits = livraisons_produits.filter(livraison__fournisseur__id=idFournisseur)
        if idProduit:
            livraisons_produits = livraisons_produits.filter(produit__id=idProduit)

        # Construction de la réponse
        resultats = []
        for lp in livraisons_produits:
            resultats.append({
                "id": lp.produit.id,
                "fournisseur": lp.livraison.fournisseur.nom,
                "produit": lp.produit.libelle,
                "quantite": lp.quantite,
                "prix": lp.prix,
                "date_livraison": lp.livraison.date.strftime("%Y-%m-%d"),
            })

        return JsonResponse({"livraisons": resultats})

    return JsonResponse({"error": "Requête invalide"}, status=400)




@login_required
def get_produit_details(request):
    produit_id = request.GET.get('produit_id')
    try:
        produit = Produit.objects.get(id=produit_id)
        data = {
            "success": True,
            "prix_achat": produit.prixAchat,  # Remplacez par le champ réel
            "prix_detail": produit.prixDetail,  # Remplacez par le champ réel
            "prix_en_gros": produit.prixEnGros,  # Remplacez par le champ réel
            "stock": produit.quantite,  # Remplacez par le champ réel
        }
    except Produit.DoesNotExist:
        data = {
            "success": False,
            "error": f"Produit avec l'ID {produit_id} introuvable."
        }
    except Exception as e:
        data = {
            "success": False,
            "error": str(e)
        }
    
    return JsonResponse(data)




from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Categorie, Produit

@login_required
def recherche_produit(request):
    if request.method == "POST":
        categorieId = request.POST.get('idCategorie')
        produitId = request.POST.get("produitId")

        produits = Produit.objects.all()  # Récupérer tous les produits par défaut

        # Filtrer par catégorie si elle est fournie
        if categorieId and categorieId != "0":
            try:
                cat = Categorie.objects.get(id=categorieId)
                produits = produits.filter(categorie=cat)
            except Categorie.DoesNotExist:
                return JsonResponse({"error": "Catégorie introuvable"}, status=404)

        # Filtrer par produit si fourni
        if produitId and produitId != "0":
            try:
                produits = produits.filter(id=produitId)
            except Produit.DoesNotExist:
                return JsonResponse({"error": "Produit introuvable"}, status=404)

        # Construire la réponse JSON
        produits_data = [
            {
                "id":produit.id,
                "code": produit.codebare,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "prixAchat": produit.prixAchat,
                "prixDetail": produit.prixDetail,
                "prixEnGros": produit.prixEnGros,
                "peremption": produit.datePeremption.strftime("%Y-%m-%d") if produit.datePeremption else None,
                "seuil": produit.seuil,
            }
            for produit in produits
        ]
        
        return JsonResponse({"produits": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)







@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def recherche_produit_livrer(request):
    if request.method == "POST":
        numFacture = request.POST.get('numFacture')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        livraisons = Livraison.objects.filter(date__gte=dateDebut, date__lte=dateFin)  # Récupérer tous les produits par défaut

        # Filtrer par numFacture si elle est fournie
        if numFacture:
            try:
                livraisons = Livraison.objects.filter(numeroFacture=numFacture, date__gte=dateDebut, date__lte=dateFin)
            except Categorie.DoesNotExist:
                return JsonResponse({"error": "Numero facture introuvable"}, status=404)

       
        # Construire la réponse JSON
        produits_data = [
            {
                "id":livraison.id,
                "fournisseur": livraison.fournisseur.nom,
                "date": livraison.date,
                "montant": LivraisonProduit.objects.filter(livraison=livraison).aggregate(total=Sum(F('quantite')*F('prix')))['total'] or 0,
                "numFacture": livraison.numeroFacture,
            }
            for livraison in livraisons
        ]
        
        return JsonResponse({"livraison": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)





"""
@login_required
def vente_create(request):
    if request.method == 'POST':
        commande_form = CommandeForm(request.POST)
        formset = CommandeProduitFormSet(request.POST)
        pret_form=pretClientForm(request.POST)

        if commande_form.is_valid() and formset.is_valid():
            with transaction.atomic():  # Ensure database integrity
                try:
                    # Save Commande
                    commande = commande_form.save(commit=False)
                    commande.user=request.user
                    commande.montantAchat=0
                    commande.save()
                    # Process each form in the formset
                    montantAchat=0
                    for form in formset:
                        if not (form.cleaned_data.get('produit') and form.cleaned_data.get('quantite')) or form.cleaned_data.get('DELETE'):
                            continue
                        
                        commande_produit = form.save(commit=False)
                        commande_produit.commande = commande

                        produit = commande_produit.produit
                        if form.cleaned_data.get('quantite') <= 0 or form.cleaned_data.get('quantite') > produit.quantite:
                            messages.error(request, "La quantité doit être suffisante et supérieure à zéro.")
                            continue

                        produit.quantite -= commande_produit.quantite

                        produit.save()

                        commande_produit.save()
                        #calcul du montantAchat
                        montantAchat+=produit.prixAchat*commande_produit.quantite

                    commande.montantAchat=montantAchat
                    commande.save()

                    if commande.typePayement == "Pret":
                        pret_form.fields['client'].required = True  # Rendre obligatoire pour "Pret"
                    else:
                        pret_form.fields['client'].required = False 

                    if commande.typePayement=="Pret":
                        pret=pret_form.save(commit=False)
                        pret.payer="Non"
                        pret.user=request.user
                        pret.commande=commande
                        pret.montant=commande.montant
                        pret.date=commande.date
                        pret.save()

                        
                        commande.client=pret.client
                        commande.save()
                    
                    messages.success(request,"Enregistrement reussi")

                    commande_form = CommandeForm()
                    formset = CommandeProduitFormSet()
                    pret_form=pretClientForm()
                    produits = Produit.objects.all()
                    return render(request, 'CommercialSoft/baseVente.html', {'commande_form': commande_form,'formset': formset,'pret_form':pret_form,'listes': produits,'recu_url': '/commerce_recu','venteId':commande.id})
                except Exception as e:
                    # Handle exceptions (log error, notify user, etc.)
                    messages.error(request,f"Erreur d'enregistrement: {e}")
        else:
            messages.error(request, f"Erreurs dans le formulaire de commande : {commande_form.errors}")
            for error in formset.errors:
                if error:  # Vérifie si l'erreur existe
                    messages.error(request, f"Erreur dans un formulaire : {error}")
    
    commande_form = CommandeForm()
    formset = CommandeProduitFormSet()
    pret_form=pretClientForm()

    produits = Produit.objects.all()
    return render(request, 'CommercialSoft/baseVente.html', {
        'commande_form': commande_form,
        'formset': formset,
        'pret_form':pret_form,
        'listes': produits,
    })
"""






@login_required
def vente_creates(request):
    if request.method == 'POST':
        commande_form = CommandeForm(request.POST)
        pret_form = pretClientForm(request.POST)
        produits_json = request.POST.get('jsonDataInput', '[]')  # JSON envoyé depuis JS
        try:
            produits_data = json.loads(produits_json)
        except json.JSONDecodeError:
            produits_data = []

        if commande_form.is_valid() and (not produits_data == []):
            with transaction.atomic():
                try:
                    # Création de la commande
                    commande = commande_form.save(commit=False)
                    commande.user = request.user
                    commande.montantAchat = 0
                    commande.save()

                    montantAchat = 0
                    montantTotal = 0

                    for item in produits_data:
                        produit_id = item.get('id')
                        quantite = int(item.get('quantite', 0))
                        prix = int(item.get('prix', 0))

                        if not produit_id or quantite <= 0:
                            continue

                        produit = Produit.objects.get(id=produit_id)

                        if quantite > produit.quantite:
                            messages.error(request, f"La quantité de {produit.libelle} est insuffisante.")
                            continue

                        produit.quantite -= quantite
                        produit.save()

                        CommandeProduit.objects.create(
                            commande=commande,
                            produit=produit,
                            quantite=quantite,
                            prix=prix
                        )

                        montantAchat += produit.prixAchat * quantite
                        montantTotal += prix * quantite

                    commande.montantAchat = montantAchat
                    commande.montant = montantTotal
                    commande.save()

                    # Gestion Pret
                    if commande.typePayement == "Pret":
                        pret_form.fields['client'].required = True
                        if pret_form.is_valid():
                            pret = pret_form.save(commit=False)
                            pret.commande = commande
                            pret.user = request.user
                            pret.montant = commande.montant
                            pret.date = commande.date
                            pret.payer = "Non"
                            pret.save()
                            commande.client = pret.client
                            commande.save()
                        else:
                            messages.error(request, "Erreur dans le formulaire de Pret.")
                    else:
                        pret_form.fields['client'].required = False

                    messages.success(request, "Enregistrement réussi !")

                    # Préparer les formulaires vides pour réaffichage
                    commande_form = CommandeForm()
                    pret_form = pretClientForm()
                    produits = Produit.objects.all()
                    return render(request, 'CommercialSoft/vente.html', {
                        'commande_form': commande_form,
                        'pret_form': pret_form,
                        'listes': produits,
                        'recu_url': '/commerce_recu',
                        'venteId': commande.id
                    })
                except Exception as e:
                    messages.error(request, f"Erreur d'enregistrement: {e}")
        else:
            messages.error(request, "Formulaire incomplet ou aucun produit sélectionné.")

    # GET ou formulaire invalide
    commande_form = CommandeForm()
    pret_form = pretClientForm()
    produits = Produit.objects.all()
    boutique= InfoBoutique.objects.first()
    return render(request, 'CommercialSoft/vente2.html', {
        'commande_form': commande_form,
        'pret_form': pret_form,
        'listes': produits,
        'user':request.user,
        'boutique': boutique,
    })











@login_required
def recherche_vente(request):
    if request.method == "POST":
        idUser = request.POST.get('idUser')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Construire le filtre dynamique
        filtre = {}

        # Ajouter les filtres pour les dates si elles sont fournies
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if idUser and idUser != "0":
            try:
                user = User.objects.get(id=idUser)
                filtre["user"] = user
            except User.DoesNotExist:
                return JsonResponse({"error": "Utilisateur introuvable"}, status=404)

        # Appliquer le filtre à la requête
        ventes = Commande.objects.filter(**filtre)
        
        montantRetour = (
                            Retour.objects
                            .filter(**filtre)
                            .annotate(montant=ExpressionWrapper(F('prix') * F('quantite'), output_field=DecimalField(max_digits=38, decimal_places=2)))
                            .aggregate(total=Sum('montant'))['total'] or 0
                        )
        
        # Construire la réponse JSON
        produits_data = [
            {
                "id": vente.id,
                "montant": vente.montant,
                "remise": vente.remise,
                "net": vente.montant - vente.remise,
                "date": vente.date,
                "user": vente.user.username if vente.user else "",
                "type": vente.typeVente,
                "payement": vente.typePayement,
                "client": vente.client.nom if vente.client else "",
                "montantAchat":vente.montantAchat,
            }
            for vente in ventes
        ]

        return JsonResponse({"vente": produits_data,"montantRetour": montantRetour})

    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def recherche_vente_client(request):
    if request.method == "POST":
        idClient = request.POST.get('idClient')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Construire le filtre dynamique
        filtre = {}

        # Ajouter les filtres pour les dates si elles sont fournies
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if idClient and idClient != "0":
            try:
                client = Client.objects.get(id=idClient)
                filtre["client"] = client
            except Client.DoesNotExist:
                return JsonResponse({"error": "Client introuvable"}, status=404)

        # Appliquer le filtre à la requête
        ventes = Commande.objects.filter(**filtre)

        # Construire la réponse JSON
        produits_data = [
            {
                "id": vente.id,
                "montant": vente.montant,
                "remise": vente.remise,
                "net": vente.montant - vente.remise,
                "date": vente.date,
                "type": vente.typeVente,
                "payement": vente.typePayement,
                "client": vente.client.nom if vente.client else "",
                "montantAchat":vente.montantAchat,
            }
            for vente in ventes
        ]

        return JsonResponse({"vente": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)





@login_required
def recherche_vente_payement(request):
    if request.method == "POST":
        payement = request.POST.get('payement')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Construire le filtre dynamique
        filtre = {}

        # Ajouter les filtres pour les dates si elles sont fournies
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if payement and payement != "0":
            try:
                filtre["typePayement"] = payement
            except :
                return JsonResponse({"error": "Payement introuvable"}, status=404)

        # Appliquer le filtre à la requête
        ventes = Commande.objects.filter(**filtre)

        # Construire la réponse JSON
        produits_data = [
            {
                "id": vente.id,
                "montant": vente.montant,
                "remise": vente.remise,
                "net": vente.montant - vente.remise,
                "date": vente.date,
                "type": vente.typeVente,
                "payement": vente.typePayement,
                "client": vente.client.nom if vente.client else "",
                "montantAchat":vente.montantAchat,
            }
            for vente in ventes
        ]

        return JsonResponse({"vente": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def recherche_vente_type(request):
    if request.method == "POST":
        type = request.POST.get('type')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Construire le filtre dynamique
        filtre = {}

        # Ajouter les filtres pour les dates si elles sont fournies
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if type and type != "0":
            try:
                filtre["typeVente"] = type
            except :
                return JsonResponse({"error": "Type introuvable"}, status=404)

        # Appliquer le filtre à la requête
        ventes = Commande.objects.filter(**filtre)

        # Construire la réponse JSON
        produits_data = [
            {
                "id": vente.id,
                "montant": vente.montant,
                "remise": vente.remise,
                "net": vente.montant - vente.remise,
                "date": vente.date,
                "type": vente.typeVente,
                "payement": vente.typePayement,
                "client": vente.client.nom if vente.client else "",
                "montantAchat":vente.montantAchat,
            }
            for vente in ventes
        ]

        return JsonResponse({"vente": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def recherche_situation_vente(request):
    if request.method == "POST":
        idProduit = request.POST.get('idProduit')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        filtre = {}
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        # Récupérer les ventes
        produits_infos = []

        if idProduit != "":
            try:
                produit = Produit.objects.get(id=idProduit)

                # Calculer quantités pour ce produit
                entree = LivraisonProduit.objects.filter(produit=produit)
                sortie = CommandeProduit.objects.filter(produit=produit)

                if dateDebut:
                    entree = entree.filter(livraison__date__gte=dateDebut)
                    sortie = sortie.filter(date__gte=dateDebut)
                if dateFin:
                    entree = entree.filter(livraison__date__lte=dateFin)
                    sortie = sortie.filter(date__lte=dateFin)

                quantite_entree = entree.aggregate(total=Sum("quantite"))["total"] or 0
                quantite_sortie = sortie.aggregate(total=Sum("quantite"))["total"] or 0
                stock = produit.quantite

                produits_infos.append({
                    "id": produit.id,
                    "libelle": produit.libelle,
                    "quantite_entree": quantite_entree,
                    "quantite_sortie": quantite_sortie,
                    "stock": stock
                })

            except Produit.DoesNotExist:
                return JsonResponse({"error": "Produit introuvable"}, status=404)

        else:
            # Parcourir tous les produits
            produits = Produit.objects.all()
            for produit in produits:
                entree = LivraisonProduit.objects.filter(produit=produit)
                sortie = CommandeProduit.objects.filter(produit=produit)

                if dateDebut:
                    entree = entree.filter(livraison__date__gte=dateDebut)
                    sortie = sortie.filter(date__gte=dateDebut)
                if dateFin:
                    entree = entree.filter(livraison__date__lte=dateDebut)
                    sortie = sortie.filter(date__lte=dateFin)

                quantite_entree = entree.aggregate(total=Sum("quantite"))["total"] or 0
                quantite_sortie = sortie.aggregate(total=Sum("quantite"))["total"] or 0
                stock = produit.quantite

                produits_infos.append({
                    "id": produit.id,
                    "libelle": produit.libelle,
                    "quantite_entree": quantite_entree,
                    "quantite_sortie": quantite_sortie,
                    "stock": stock
                })

        return JsonResponse({
            "vente": produits_infos
        })

    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def produit_par_vente(request):
    if request.method == "GET":
        vente_id = request.GET.get('vente_id')

        commande=Commande.objects.get(id=vente_id)
        commandesP = CommandeProduit.objects.filter(commande=commande)

        # Construire la réponse JSON
        produits_data = [
            {
                "id": commandeP.id,
                "produit": commandeP.produit.libelle if commandeP.produit else "inconu",
                "quantite": commandeP.quantite,
            }
            for commandeP in commandesP
        ]

        return JsonResponse({"listes": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def recherche_detail_vente(request):
    if request.method == "GET":
        idUser = request.GET.get('idUser')
        dateDebut = request.GET.get("dateDebut")
        dateFin = request.GET.get("dateFin")

        filtre = {}

        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        if idUser and idUser != "0":
            try:
                user = User.objects.get(id=idUser)
                filtre["user"] = user
            except User.DoesNotExist:
                return JsonResponse({"error": "Utilisateur introuvable"}, status=404)

        commandes = Commande.objects.filter(**filtre)
        produits_data = []

        for commande in commandes:
            commandesP = CommandeProduit.objects.filter(commande=commande).order_by('id')
            for commandeP in commandesP:
                produits_data.append({
                    "id": commandeP.id,
                    "produit": commandeP.produit.libelle if commandeP.produit else "inconnu",
                    "quantite": commandeP.quantite,
                    "prix" : commandeP.prix,
                    "date" : commandeP.date,
                    "montant" : commandeP.prix*commandeP.quantite,
                })

        return JsonResponse({"listes": produits_data}, safe=False)

    return JsonResponse({"error": "Requête invalide"}, status=400)






@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def vente_delete(request, pk):
    commande = get_object_or_404(Commande, pk=pk)

    try:
        with transaction.atomic():
            # Met à jour les quantités des produits
            for commandeP in commande.commandeproduit_set.all():
                produit = commandeP.produit
                produit.quantite += commandeP.quantite  # Réajoute la quantité au stock
                produit.save()

            # Supprime la commande
            commande.delete()
            messages.success(request, "Vente supprimée avec succès !")

    except IntegrityError:
        messages.error(request, "Erreur : Cette vente est liée à d'autres entités et ne peut pas être supprimée.")
    
    return redirect('commerce_produitVendu')





@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def commandeP_delete(request):
    myid = request.POST.get("id")
    commandeP = CommandeProduit.objects.get(id=myid)
    with transaction.atomic():
        try:
            commandeP.delete()
            commande=commandeP.commande
            montant=commande.montant
            newMontant=montant-commandeP.prix
            commande.montant=newMontant
            produit=commandeP.produit
            produit.quantite += commandeP.quantite
            produit.save()
            commande.save()
            return JsonResponse({"success": True, "message": "Produit supprimé avec succès !"})
        except IntegrityError:
            return JsonResponse({"success": False, "message": "Erreur: Impossible de supprimer ce produit."}, status=400)





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def produit_edit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == "POST":
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, "Produit mise à jour avec succès!")
            return redirect('commerce_produit')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la produit.")
    else:
        form = ProduitForm(instance=produit)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def modifier_commande(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == "POST":
        form = CommandeForm(request.POST, instance=commande)
        if form.is_valid():
            form.save()
            messages.success(request, "Vente modifiée avec succès!")
            return redirect('commerce_produitVendu')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la produit.")
    else:
        form = CommandeForm(instance=commande)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})





 # Example for Patient Views
@user_passes_test(est_administrateur,est_gestionnaire)
@login_required
def produit_delete(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    try:
        produit.delete()
        messages.success(request, "Produit supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette produit est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_produit')








# examen Views
@login_required
def depense_list_create(request):
    if request.method == "POST":
        form = DepenseForm(request.POST)
        if form.is_valid():
            depense= form.save(commit=False)  # Sauvegarder après modification
            depense.user=request.user
            depense.save()
            messages.success(request, "Dépense créée avec succès !")
            return redirect('commerce_depense')
        else:
            messages.error(request, "Erreur lors de la création de la dépense.")
    else:
        form = DepenseForm()
    
    depense = Depense.objects.all().order_by('-date')
    paginator = Paginator(depense, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/depense.html', {'form': form,'listes': paginated_depense})




@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def depense_edit(request, pk):
    depense = get_object_or_404(Depense, pk=pk)
    if request.method == "POST":
        form = DepenseForm(request.POST, instance=depense)
        if form.is_valid():
            form.save()
            messages.success(request, "Depense mise à jour avec succès!")
            return redirect('commerce_depense')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la depense.")
    else:
        form = DepenseForm(instance=depense)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})





 # Example for Patient Views
@login_required
def depense_list(request):
    categorie=DepenseForm()
    return render(request, 'CommercialSoft/listeDepense.html',{'form':categorie})





@login_required
def recherche_depense(request):
    if request.method == "POST":
        numero = request.POST.get('idCategorie', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            categorie = Categorie_Depense.objects.get(id=numero)
            depenses=Depense.objects.filter(categorie=categorie,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            depenses=Depense.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": depense.id,
                "intitule": depense.intitule,
                "quantite":depense.quantite,
                "prix": depense.prix,
                "montant":depense.quantite*depense.prix,
                "date": depense.date,
                "categorie":depense.categorie.nom,
            }
            for depense in depenses
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def depense_delete(request, pk):
    depense = get_object_or_404(Depense, pk=pk)
    try:
        depense.delete()
        messages.success(request, "Depense supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette depense est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_depense')






@login_required
def categorie_depense_list_create(request):
    if request.method == "POST":
        form = CategorieDepenseForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Categorie créée avec succès !")
            return redirect('commerce_categorieDepense')
        else:
            messages.error(request, "Erreur lors de la création de la categorie.")
    else:
        form = CategorieDepenseForm()
    
    categorie = Categorie_Depense.objects.all()
    paginator = Paginator(categorie, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/categorieDepense.html', {'form': form,'listes': paginated_depense})





@login_required
def categorie_depense_edit(request, pk):
    categorie = get_object_or_404(Categorie_Depense, pk=pk)
    if request.method == "POST":
        form = CategorieDepenseForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, "Categorie mise à jour avec succès!")
            return redirect('commerce_categorieDepense')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la categorie.")
    else:
        form = CategorieDepenseForm(instance=categorie)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


@login_required
def categorie_depense_delete(request, pk):
    categorie = get_object_or_404(Categorie_Depense, pk=pk)
    try:
        categorie.delete()
        messages.success(request, "Categorie supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette categorie est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_categorieDepense')






def imprimer_recu_versement(request, versement_id):
    versement = get_object_or_404(VersementClient, id=versement_id)

    total_prets = PretClient.objects.filter(client=versement.client) \
                                    .aggregate(total=Sum('montant'))['total'] or 0

    total_versements = VersementClient.objects.filter(client=versement.client) \
                                              .aggregate(total=Sum('montant'))['total'] or 0

    reste = total_prets - total_versements
    if reste < 0:
        reste = 0

    context = {
        'client': versement.client.nom,
        'montant': versement.montant,
        'date': versement.date,
        'reste': reste,
        'user': versement.user,
    }
    return render(request, 'CommercialSoft/pdfRecuVersementClient.html', context)







# examen Views
@login_required
def versementClient_list_create(request):
    if request.method == "POST":
        form = VersementClientForm(request.POST)
        if form.is_valid():
            versement= form.save(commit=False)  # Sauvegarder après modification
            versement.user=request.user
            versement.save()
            messages.success(request, "Versement créée avec succès !")
            return redirect('imprimer_recu_versement', versement.id)
            return redirect('commerce_versementClient')
        else:
            messages.error(request, "Erreur lors de la création du versement.")
    else:
        form = VersementClientForm()
    
    versementClient = VersementClient.objects.all().order_by('-date')
    paginator = Paginator(versementClient, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/versementClient.html', {'form': form,'listes': paginated_depense})




from django.utils import timezone
from django.db.models import Sum

def imprimer_situation_client(request, client_id):
    client = Client.objects.get(id=client_id)

    total_prets = PretClient.objects.filter(client=client) \
                                    .aggregate(total=Sum('montant'))['total'] or 0

    total_versements = VersementClient.objects.filter(client=client) \
                                              .aggregate(total=Sum('montant'))['total'] or 0

    reste = total_prets - total_versements
    if reste < 0:
        reste = 0

    date_impression = timezone.now()

    context = {
        'client': client,
        'reste': reste,
        'date_impression': date_impression,
    }
    return render(request, 'CommercialSoft/pdfSituationRecuClient.html', context)





@login_required
def versementClient_edit(request, pk):
    versementClient = get_object_or_404(VersementClient, pk=pk)
    if request.method == "POST":
        form = VersementClientForm(request.POST, instance=versementClient)
        if form.is_valid():
            form.save()
            messages.success(request, "Versement mise à jour avec succès!")
            return redirect('commerce_versementClient')
        else:
            messages.error(request, "Erreur lors de la mise à jour du versement.")
    else:
        form = VersementClientForm(instance=versementClient)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@login_required
def versementClient_list(request):
    client=VersementClient()
    return render(request, 'CommercialSoft/listeClient.html',{'form':client})





@login_required
def recherche_versementClient(request):
    if request.method == "POST":
        numero = request.POST.get('idClient', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            client = client.objects.get(id=numero)
            versementClients=VersementClient.objects.filter(client=client,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            versementClients=VersementClient.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": versement.id,
                "montant": versement.montant,
                "date":versement.date,
            }
            for versement in versementClients
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def versementClient_delete(request, pk):
    versement = get_object_or_404(VersementClient, pk=pk)
    try:
        versement.delete()
        messages.success(request, "versement supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce versement est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_versementClient')









# examen Views
@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def versementGerant_list_create(request):
    if request.method == "POST":
        form = VersementGerantForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Versement créée avec succès !")
            return redirect('commerce_versementGerant')
        else:
            messages.error(request, "Erreur lors de la création du versement.")
    else:
        form = VersementGerantForm()
    
    versementGerant = VersementGerant.objects.all().order_by('-date')
    paginator = Paginator(versementGerant, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/versementGerant.html', {'form': form,'listes': paginated_depense})



@login_required
@user_passes_test(est_administrateur)
def versementGerant_edit(request, pk):
    versementGerant = get_object_or_404(VersementGerant, pk=pk)
    if request.method == "POST":
        form = VersementGerantForm(request.POST, instance=versementGerant)
        if form.is_valid():
            form.save()
            messages.success(request, "Versement mise à jour avec succès!")
            return redirect('commerce_versementGerant')
        else:
            messages.error(request, "Erreur lors de la mise à jour du versement.")
    else:
        form = VersementGerantForm(instance=versementGerant)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@login_required
def versementGerant_list(request):
    agent=VersementGerantForm()
    return render(request, 'CommercialSoft/listeVersementGerant.html',{'form':agent})





@login_required
def recherche_versementGerant(request):
    if request.method == "POST":
        numero = request.POST.get('idGerant', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            user = User.objects.get(id=numero)
            versementGerants=VersementGerant.objects.filter(user=user,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            versementGerants=VersementGerant.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": versement.id,
                "montant": versement.montant,
                "date":versement.date,
                "user": versement.user.first_name +" "+versement.user.last_name
            }
            for versement in versementGerants
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def versementGerant_delete(request, pk):
    versement = get_object_or_404(VersementGerant, pk=pk)
    try:
        versement.delete()
        messages.success(request, "versement supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce versement est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_versementGerant')






# examen Views
@login_required
def pretClient_list_create(request):
    if request.method == "POST":
        form = detteClientForm(request.POST)
        if form.is_valid():
            dette = form.save(commit=False)
            dette.user=request.user
            dette.save()  # Sauvegarder après modification
            messages.success(request, "pret créée avec succès !")
            return redirect('commerce_pretClient')
        else:
            messages.error(request, "Erreur lors de la création de la pret.")
    else:
        form = detteClientForm()
    
    pret = PretClient.objects.all().order_by('-date')
    paginator = Paginator(pret, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/pretClient.html', {'form': form,'listes': paginated_depense})



@login_required
def pretClient_edit(request, pk):
    pret = get_object_or_404(PretClient, pk=pk)
    if request.method == "POST":
        form = detteClientForm(request.POST, instance=pret)
        if form.is_valid():
            form.save()
            messages.success(request, "Pret mise à jour avec succès!")
            return redirect('commerce_pretClient')
        else:
            messages.error(request, "Erreur lors de la mise à jour du pret.")
    else:
        form = detteClientForm(instance=pret)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@login_required
def pretClient_list(request):
    client=detteClientForm()
    return render(request, 'CommercialSoft/listePretClient.html',{'form':client})


@login_required
def detail_pret_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    dette=PretClient.objects.filter(client=client)
    payement=VersementClient.objects.filter(client=client)

    total_dette=PretClient.objects.aggregate(total=Sum('montant'))['total'] or 0
    total_payement=VersementClient.objects.aggregate(total=Sum('montant'))['total'] or 0

    return render(request, 'CommercialSoft/detailPretClient.html', {'dettes': dette,'payements':payement,'total_dette': separateur(total_dette), 'total_payement': separateur(total_payement),'client':client})





@login_required
def recherche_pretClient(request):
    if request.method == "POST":
        numero = request.POST.get('idClient', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        filtre = {}

        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin
        if numero:
            client = Client.objects.get(id=numero)
            filtre["client"]=client
        if numero :  # Si un numéro est saisi
            
            pretClients=PretClient.objects.filter(**filtre)
        else:  # Sinon, afficher les patients du jour
            pretClients=PretClient.objects.filter(**filtre)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": pret.id,
                "client": pret.client.nom,
                "montant":pret.montant,
                "date": pret.date,
                "dateEcheance":pret.dateEcheance,
                "commentaire":pret.commentaire or "",
                "user": pret.user.first_name+ " "+pret.user.last_name,
            }
            for pret in pretClients
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
def pretClient_delete(request, pk):
    pret = get_object_or_404(PretClient, pk=pk)
    try:
        pret.delete()
        messages.success(request, "pret supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cet pret est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_pretClient')







# examen Views
@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def versementFournisseur_list_create(request):
    if request.method == "POST":
        form = VersementFournisseurForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Versement créée avec succès !")
            return redirect('commerce_versementFournisseur')
        else:
            messages.error(request, "Erreur lors de la création du versement.")
    else:
        form = VersementFournisseurForm()
    
    versementFournisseur = VersementFournisseur.objects.all().order_by('-date')
    paginator = Paginator(versementFournisseur, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/versementFournisseur.html', {'form': form,'listes': paginated_depense})



@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def versementFournisseur_edit(request, pk):
    versementFournisseur = get_object_or_404(VersementFournisseur, pk=pk)
    if request.method == "POST":
        form = VersementFournisseurForm(request.POST, instance=versementFournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, "Versement mise à jour avec succès!")
            return redirect('commerce_versementFournisseur')
        else:
            messages.error(request, "Erreur lors de la mise à jour du versement.")
    else:
        form = VersementFournisseurForm(instance=versementFournisseur)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def versementFournisseur_list(request):
    fournisseur=VersementFournisseur()
    return render(request, 'CommercialSoft/listeDepense.html',{'form':fournisseur})





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def recherche_versementFournisseur(request):
    if request.method == "POST":
        numero = request.POST.get('idFournisseur', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            fournisseur = Fournisseur.objects.get(id=numero)
            versementFournisseurs=VersementFournisseur.objects.filter(fournisseur=fournisseur,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            versementFournisseurs=VersementFournisseur.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": versement.id,
                "montant": versement.montant,
                "date":versement.date,
            }
            for versement in versementFournisseurs
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def versementFournisseur_delete(request, pk):
    versement = get_object_or_404(VersementFournisseur, pk=pk)
    try:
        versement.delete()
        messages.success(request, "versement supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce versement est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_versementFournisseur')







# examen Views
@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def detteFournisseur_list_create(request):
    if request.method == "POST":
        form = DetteFournisseurForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Dette créée avec succès !")
            return redirect('commerce_detteFournisseur')
        else:
            messages.error(request, "Erreur lors de la création de la dette.")
    else:
        form = DetteFournisseurForm()
    
    detteFournisseur = DetteFournisseur.objects.all().order_by('-date')
    paginator = Paginator(detteFournisseur, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/detteFournisseur.html', {'form': form,'listes': paginated_depense})



@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def detteFournisseur_edit(request, pk):
    detteFournisseur = get_object_or_404(DetteFournisseur, pk=pk)
    if request.method == "POST":
        form = DetteFournisseurForm(request.POST, instance=detteFournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, "Dette mise à jour avec succès!")
            return redirect('commerce_detteFournisseur')
        else:
            messages.error(request, "Erreur lors de la mise à jour du versement.")
    else:
        form = DetteFournisseurForm(instance=detteFournisseur)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})







@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def recherche_detteFournisseur(request):
    if request.method == "POST":
        numero = request.POST.get('idFournisseur', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            fournisseur = Fournisseur.objects.get(id=numero)
            detteFournisseurs=DetteFournisseur.objects.filter(fournisseur=fournisseur,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            detteFournisseurs=DetteFournisseur.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": dette.id,
                "montant": dette.montant,
                "date":dette.date,
            }
            for dette in detteFournisseurs
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)






@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def detteFournisseur_delete(request, pk):
    dette = get_object_or_404(DetteFournisseur, pk=pk)
    try:
        dette.delete()
        messages.success(request, "dette supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce dette est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_detteFournisseur')





# examen Views
@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def client_list_create(request):
    if request.method == "POST":
        form = clientForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Client créée avec succès !")
            return redirect('commerce_client')
        else:
            messages.error(request, "Erreur lors de la création du client.")
    else:
        form = clientForm()
    
    client = Client.objects.all()
    paginator = Paginator(client, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/client.html', {'form': form,'listes': paginated_depense})



@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = clientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client mise à jour avec succès!")
            return redirect('commerce_client')
        else:
            messages.error(request, "Erreur lors de la mise à jour du client.")
    else:
        form = clientForm(instance=client)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})


 # Example for Patient Views
@login_required
def client_list(request):
    client=clientForm()
    liste=Client.objects.all()
    return render(request, 'CommercialSoft/listeClient.html',{'form':client,'listes':liste})





@login_required
def recherche_client(request):
    if request.method == "POST":
        numero = request.POST.get('idClient', '0').strip()  # Récupérer le numéro envoyé
        numero=int(numero)
        
        clients = Client.objects.filter(id=numero) if numero else Client.objects.all()
        
        print(f"Valeur de numero : '{numero}'")  # Debugging
        # Construire une réponse JSON
        clients_data = [
            {
                "id": client.id,
                "nom": client.nom,
                "telephone": client.telephone,
                "email": client.email,
                "adresse": client.adresse,
                "matricule": client.matricule,
                "pourcentage": client.pourcentage,
                "detteMaximale": client.detteMaximale,
                "total_pret": client.prets.aggregate(Sum('montant'))['montant__sum'] or 0,
                "total_versement": client.versements.aggregate(Sum('montant'))['montant__sum'] or 0,
                "balance": (client.prets.aggregate(Sum('montant'))['montant__sum'] or 0) - 
                           (client.versements.aggregate(Sum('montant'))['montant__sum'] or 0),
            }
            for client in clients
        ]

        
        return JsonResponse({"clients": clients_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)





@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    try:
        client.delete()
        messages.success(request, "client supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce client est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_client')







# examen Views
@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def societe_list_create(request):
    if request.method == "POST":
        form = societeForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "societe créée avec succès !")
            return redirect('commerce_societe')
        else:
            messages.error(request, "Erreur lors de la création de la societe.")
    else:
        form = societeForm()
    
    societe = Societe.objects.all()
    paginator = Paginator(societe, 15)
    page = request.GET.get('page')
    paginated_depense = paginator.get_page(page)
    
    return render(request, 'CommercialSoft/societe.html', {'form': form,'listes': paginated_depense})



@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def societe_edit(request, pk):
    societe = get_object_or_404(Societe, pk=pk)
    if request.method == "POST":
        form = societeForm(request.POST, instance=societe)
        if form.is_valid():
            form.save()
            messages.success(request, "Societe mise à jour avec succès!")
            return redirect('commerce_societe')
        else:
            messages.error(request, "Erreur lors de la mise à jour de la societe.")
    else:
        form = societeForm(instance=societe)
    
    return render(request, 'CommercialSoft/modification.html', {'form': form})





@login_required
@user_passes_test(est_administrateur, est_gestionnaire)
def societe_delete(request, pk):
    societe = get_object_or_404(Societe, pk=pk)
    try:
        societe.delete()
        messages.success(request, "societe supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce societe est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_societe')




@login_required
@user_passes_test(est_administrateur, est_gestionnaire, est_comptable)
def bilan(request):
    users = User.objects.all()
    return render(request, 'CommercialSoft/bilan.html',{'users':users})




@login_required
@user_passes_test(est_administrateur, est_gestionnaire, est_comptable)
def recherche_bilan(request):
    if request.method == "POST":
        idUser = request.POST.get('idUser')
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        # Construire le filtre dynamique
        filtre = {}

        # Ajouter les filtres pour les dates si elles sont fournies
        if dateDebut:
            filtre["date__gte"] = dateDebut
        if dateFin:
            filtre["date__lte"] = dateFin

        

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if idUser and idUser != "0":
            try:
                user = User.objects.get(id=idUser)
                filtre["user"] = user
            except User.DoesNotExist:
                return JsonResponse({"error": "Utilisateur introuvable"}, status=404)
            
        #pret reclamer
        pretReclamer = VersementClient.objects.filter(**filtre)
        depense = Depense.objects.filter(**filtre)

        # Appliquer le filtre à la requête
        retour=Retour.objects.filter(**filtre)
        ventes = Commande.objects.filter(**filtre)
        pret=PretClient.objects.filter(**filtre)
        
        # Calculer les totaux
        total_montant = ventes.aggregate(Sum('montant'))['montant__sum'] or 0
        total_remise = ventes.aggregate(Sum('remise'))['remise__sum'] or 0
        total_net_vente = total_montant - total_remise  # Calcul de la différence
        # pret reclamer
        total_pretReclamer = pretReclamer.aggregate(Sum('montant'))['montant__sum'] or 0
        total_pret = pret.aggregate(Sum('montant'))['montant__sum'] or 0
        
        total_depense = depense.aggregate(total=Sum(F('quantite') * F('prix')))['total'] or 0

        total_retour = retour.aggregate(total=Sum(F('quantite')* F('prix')))['total'] or 0

        caisse=total_net_vente+total_pretReclamer-total_pret-total_depense-total_retour or 0

        # Retourner la réponse JSON
        return JsonResponse({
            "totalVente": total_net_vente,
            "totalPretReclame": total_pretReclamer,
            "totalPret": total_pret,
            "totalDepense":total_depense,
            "totalRetour":total_retour,
            "caisse":caisse
        })

    return JsonResponse({"error": "Requête invalide"}, status=400)







 # Example for Patient Views
@user_passes_test(est_administrateur)
@login_required
def situation_boutique(request):
    return render(request, 'CommercialSoft/situationBoutique.html')




@user_passes_test(est_administrateur)
@login_required
def recherche_situation_boutique(request):
    if request.method == "POST":
        typePrix = request.POST.get('typePrix')

        # Mapping des types de prix aux attributs correspondants
        prix_mapping = {
            "achat": "prixAchat",
            "enGros": "prixEnGros",  # Correction ici
            "detail": "prixDetail"
        }

        # Vérification de la validité du typePrix
        if typePrix not in prix_mapping:
            return JsonResponse({"error": "Type de prix invalide"}, status=400)

        # Récupération des produits
        produits = Produit.objects.all()
        
        # Construction des données de réponse
        clients_data = [
            {
                "id": produit.id,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "prix": getattr(produit, prix_mapping[typePrix]),  # Accès dynamique à l'attribut
                "montant": produit.quantite * getattr(produit, prix_mapping[typePrix]),
                "montantAchat":produit.quantite*produit.prixAchat,
            }
            for produit in produits
        ]

        return JsonResponse({"clients": clients_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)





 # Example for Patient Views
@user_passes_test(est_administrateur)
@login_required
def benefice_sur_vente(request):
    return render(request, 'CommercialSoft/beneficeSurVente.html')





@login_required
@user_passes_test(est_administrateur)
def recherche_benefice_sur_vente(request):
    if request.method == "POST":
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        commandes=Commande.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": commande.id,
                "montantAchat": commande.montantAchat,
                "montantVente":commande.montant,
                "remise": commande.remise,
                "net":commande.montant-commande.remise,
                "benefice": commande.montant-commande.montantAchat,
            }
            for commande in commandes
        ]
        
        return JsonResponse({"patients": patients_data})
    
    return JsonResponse({"error": "Requête invalide"}, status=400)








#************************************** Etat **************************************************

from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse, JsonResponse
import os

def convert_html_to_pdf(source_html, output_filename):
    # Ouvre le fichier de destination pour écrire le PDF
    with open(output_filename, "w+b") as result_file:
        # Crée le PDF à partir du contenu HTML
        pisa_status = pisa.CreatePDF(source_html, dest=result_file)
    
    return pisa_status.err

def generate_pdf_from_template(template_name, context, output_filename):
    # Charge le fichier HTML à partir du répertoire templates
    template = get_template(template_name)
    html_content = template.render(context)
    
    # Appel de la fonction pour générer le PDF
    return convert_html_to_pdf(html_content, output_filename)

# Exemple d'utilisation
def recu(request, pk):
    if pk is None:
        return render(request, 'commerce/baseVente.html', {"message": "Pas d'ID fourni"})
    # Données contextuelles pour le template HTML (vous pouvez ajuster cela)
    commande=get_object_or_404(Commande,id=pk)
    produits=CommandeProduit.objects.filter(commande=commande)
    total=0
    for produit in produits:
        produit.montant = produit.prix * produit.quantite
        total+=produit.montant
    total_formatte = intcomma(total).replace(",", ".")
    net=total-commande.remise 
    net_formatte = intcomma(net).replace(",", ".")
    infoBoutique=InfoBoutique.objects.first()
    context = {'listes': produits,'total':total_formatte,'net':net_formatte,'remise':commande.remise,'boutique':infoBoutique,'commande':commande}
    
    # Chemin vers le fichier HTML dans le répertoire templates
    template_name = 'CommercialSoft/recuVente.html'  # Chemin relatif à partir du répertoire templates
    output_filename = 'facture.pdf'  # Nom du fichier PDF généré
    
    # Générer le PDF à partir du template
    generate_pdf_from_template(template_name, context, output_filename)

    # Renvoyer le fichier PDF comme réponse HTTP
    with open(output_filename, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{output_filename}"'
        return response
    





import json
from django.shortcuts import render
from django.contrib.humanize.templatetags.humanize import intcomma
from datetime import date

from CommercialSoft.models import Client, InfoBoutique  # ✅ importer en haut

def recu_offline(request):
    if request.method != "POST":
        return HttpResponse("Méthode non autorisée", status=405)

    try:
        raw_data = request.POST.get("jsonData", "{}")
        data = json.loads(raw_data)

        # Construire produits + totaux
        produits = []
        total = 0
        for item in data.get("lignes", []):
            prix = int(str(item.get("prix", 0)).replace(" ", ""))
            quantite = int(item.get("quantite", 0))
            montant = prix * quantite
            produits.append({
                "produit": {"libelle": item.get("nom", "")},
                "quantite": quantite,
                "prix": prix,
                "montant": montant
            })
            total += montant

        remise = int(str(data.get("remise", 0)).replace(" ", "")) if data.get("remise") else 0
        net = total - remise
        total_formatte = intcomma(total).replace(",", ".")
        net_formatte = intcomma(net).replace(",", ".")

        commande = {
            "id": "_____",
            "date": data.get("date", str(date.today())),
            "client": None
        }

        client_id = data.get("client")
        if client_id:
            from CommercialSoft.models import Client
            try:
                commande["client"] = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                commande["client"] = f"Client #{client_id}"

        from CommercialSoft.models import InfoBoutique
        infoBoutique = InfoBoutique.objects.first()

        context = {
            "listes": produits,
            "total": total_formatte,
            "net": net_formatte,
            "remise": remise,
            "boutique": infoBoutique,
            "commande": commande
        }

        template_name = 'CommercialSoft/recuVente.html'
        output_filename = 'recu_offline.pdf'

        # 🔥 Générer le PDF
        generate_pdf_from_template(template_name, context, output_filename)

        # 🔥 Lire le fichier et le renvoyer comme HttpResponse
        with open(output_filename, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response

    except Exception as e:
        return HttpResponse(f"Erreur lors de la génération du reçu : {str(e)}", status=400)









def generate_pdf_response_vrais(template_src, context_dict):
    try:
        print("Chargement du template...")
        template = get_template(template_src)
    except Exception as e:
        print(f"Erreur de chargement du template : {e}")
        return HttpResponse(f"Erreur de chargement du template : {e}", status=500)

    try:
        print("Rendu du HTML avec le contexte...")
        html = template.render(context_dict)
        print("HTML rendu avec succès.")
    except Exception as e:
        print(f"Erreur lors du rendu du template : {e}")
        traceback.print_exc()
        return HttpResponse(f"Erreur dans le template : {e}", status=500)

    result = BytesIO()
    try:
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        if not pdf.err:
            print("PDF généré avec succès.")
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="produit_disponible.pdf"'
            return response
        else:
            print("Erreur pisa : PDF non généré")
            return HttpResponse("Erreur lors de la génération du PDF", status=500)
    except Exception as e:
        print(f"Erreur de génération PDF : {e}")
        traceback.print_exc()
        return HttpResponse(f"Erreur lors de la conversion en PDF : {e}", status=500)





# -------------------------- Vue PDF des produits disponibles -----------------------
def pdf_Produit_disponible(request):
    if request.method == "POST":
        categorieId = request.POST.get('idCategorie')
        produitId = request.POST.get("produitId")

        produits = Produit.objects.all()

        # Filtrer par catégorie si valide
        if categorieId:
            try:
                produits = produits.filter(categorie__id=int(categorieId))
            except (ValueError, Categorie.DoesNotExist):
                return JsonResponse({"error": "Catégorie invalide ou introuvable"}, status=400)

        # Filtrer par produit si valide
        if produitId:
            try:
                produits = produits.filter(id=int(produitId))
            except (ValueError, Produit.DoesNotExist):
                return JsonResponse({"error": "Produit invalide ou introuvable"}, status=400)

        # Construire les données
        produits_data = [
            {
                "id": produit.id,
                "code": produit.codebare,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "prixAchat": produit.prixAchat,
                "prixDetail": produit.prixDetail,
                "prixEnGros": produit.prixEnGros,
                "peremption": produit.datePeremption.strftime("%Y-%m-%d") if produit.datePeremption else None,
                "seuil": produit.seuil,
            }
            for produit in produits
        ]

        
        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfProduitDisponible.html", context)

    return HttpResponse("Méthode non autorisée", status=405)






# -------------------------- Vue PDF des produits disponibles -----------------------
def pdf_inventaire(request):
    if request.method == "POST":
        categorieId = request.POST.get('idCategorie')
        produitId = request.POST.get("produitId")

        produits = Produit.objects.all()

        # Filtrer par catégorie si valide
        if categorieId and categorieId != "0":
            try:
                produits = produits.filter(categorie__id=int(categorieId))
            except (ValueError, Categorie.DoesNotExist):
                return JsonResponse({"error": "Catégorie invalide ou introuvable"}, status=400)

        # Filtrer par produit si valide
        if produitId and produitId != "0":
            try:
                produits = produits.filter(id=int(produitId))
            except (ValueError, Produit.DoesNotExist):
                return JsonResponse({"error": "Produit invalide ou introuvable"}, status=400)

        # Construire les données
        produits_data = [
            {
                "id": produit.id,
                "code": produit.codebare,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
            }
            for produit in produits
        ]

        
        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfInventaire.html", context)

    return HttpResponse("Méthode non autorisée", status=405)












    


#--------------------------liste des produits livrer -----------------------
# Exemple d'utilisation
def pdf_Produit_livrer(request):
    if request.method =="POST":
        livraisonId= request.POST.get('idLivraison')

        livraison=Livraison.objects.get(id=livraisonId)
        produits=LivraisonProduit.objects.filter(livraison=livraison)
        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": produit.id,
                "libelle": produit.produit.libelle,
                "quantite": produit.quantite,
                "prixAchat": produit.prix,
                "montant": produit.quantite*produit.prix,
            }
            for produit in produits
        ]

        montant = sum(produit["montant"] for produit in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        
        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfProduitLivrer.html", context)

    return HttpResponse("Méthode non autorisée", status=405)




#--------------------------liste des produits livrer -----------------------
# Exemple d'utilisation
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # juste pour test si CSRF gêne
def pdf_etat_depense(request):
    if request.method == "POST":
        try:
            dateDebut = request.POST.get('dateDebut')
            dateFin = request.POST.get('dateFin')
            categorie_id = request.POST.get('idCategorie')

            depenses = Depense.objects.filter(date__gte=dateDebut, date__lte=dateFin)


            if categorie_id:
                try:
                    categorie = Categorie_Depense.objects.get(id=categorie_id)
                    depenses = depenses.filter(categorie=categorie)
                except Categorie_Depense.DoesNotExist:
                    return JsonResponse({"error": "Catégorie invalide ou introuvable"}, status=404)
                
            produits_data = []
            for depense in depenses:
                montant = (depense.quantite or 0) * (depense.prix or 0)
                produits_data.append({
                    "code": depense.id,
                    "intitule": depense.intitule,
                    "quantite": depense.quantite,
                    "prix": depense.prix,
                    "date": depense.date,
                    "categorie": depense.categorie,
                    "montant": montant,
                })

            montant_total = sum(p["montant"] for p in produits_data)
            montant_formate = "{:,.0f}".format(montant_total).replace(",", " ")

            infoBoutique = InfoBoutique.objects.first()

            context = {
                'listes': produits_data,
                'montant': montant_formate,
                'boutique': infoBoutique
            }

            return generate_pdf_response_vrais("CommercialSoft/pdfEtatDepense.html", context)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return HttpResponse("Méthode non autorisée", status=405)




#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_versementClient(request):
    if request.method =="POST":
        dateDebut= request.POST.get('dateDebut')
        dateFin= request.POST.get('dateFin')
        clientId= request.POST.get('idClient')

        versements=VersementClient.objects.filter(date__gte=dateDebut, date__lte=dateFin)

        # Filtrer par catégorie si elle est fournie
        if clientId:
            try:
                client = Client.objects.get(id=clientId)
                versements=VersementClient.objects.filter(client=client,date__gte=dateDebut, date__lte=dateFin)
            except VersementClient.DoesNotExist:
                return JsonResponse({"error": "Client introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": versement.id,
                "montant": versement.montant,
                "date": versement.date,
            }
            for versement in versements
        ]

        montant = sum(versement["montant"] for versement in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatVersementClient.html", context)

    return HttpResponse("Méthode non autorisée", status=405)






#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_versementFournisseur(request):
    if request.method =="POST":
        dateDebut= request.POST.get('dateDebut')
        dateFin= request.POST.get('dateFin')
        fournisseurId= request.POST.get('idFournisseur')

        versements=VersementFournisseur.objects.filter(date__gte=dateDebut, date__lte=dateFin)

        # Filtrer par catégorie si elle est fournie
        if fournisseurId:
            try:
                fournisseur = Fournisseur.objects.get(id=fournisseurId)
                versements=VersementFournisseur.objects.filter(fournisseur=fournisseur,date__gte=dateDebut, date__lte=dateFin)
            except VersementFournisseur.DoesNotExist:
                return JsonResponse({"error": "fournisseur introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": versement.id,
                "montant": versement.montant,
                "date": versement.date,
            }
            for versement in versements
        ]

        montant = sum(versement["montant"] for versement in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatVersementFournisseur.html", context)

    return HttpResponse("Méthode non autorisée", status=405)





#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_client(request):
    if request.method =="POST":
        societeId= request.POST.get('idSociete')

        clients=Client.objects.filter()

        # Filtrer par catégorie si elle est fournie
        if societeId:
            try:
                societe = Societe.objects.get(id=societeId)
                clients=Client.objects.filter(societe=societe)
            except Client.DoesNotExist:
                return JsonResponse({"error": "Client introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": client.id,
                "nom": client.nom,
                "telephone": client.telephone,
                "adresse": client.adresse,
                "email": client.email,
                "matricule":client.matricule,
                "pourcentage":client.pourcentage,
                "detteMaximale":client.detteMaximale,
            }
            for client in clients
        ]

        montant = sum(client["montant"] for client in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
          
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatClient.html", context)

    return HttpResponse("Méthode non autorisée", status=405)




#--------------------------liste des Versement des client -----------------------
def pdf_etat_situation_client(request):
    if request.method == "POST":
        id_client_str = request.POST.get('idClient')

        if id_client_str and id_client_str != '0':  # Si un ID spécifique est fourni et différent de '0'
            try:
                id_client = int(id_client_str)
                clients = Client.objects.filter(id=id_client)

                if not clients.exists():
                    return JsonResponse({"error": "Client introuvable"}, status=404)

            except ValueError:
                return JsonResponse({"error": "ID du client invalide"}, status=400)
        else:
            clients = Client.objects.all()  # Si '0' ou rien => tous les clients

        # Reste du traitement…
        produits_data = []
        for client in clients:
            total_pret = client.prets.aggregate(Sum('montant'))['montant__sum'] or 0
            total_versement = client.versements.aggregate(Sum('montant'))['montant__sum'] or 0
            balance = total_pret - total_versement

            produits_data.append({
                "id": client.id,
                "nom": client.nom,
                "telephone": client.telephone,
                "email": client.email,
                "adresse": client.adresse,
                "matricule": client.matricule,
                "pourcentage": client.pourcentage,
                "detteMaximale": client.detteMaximale,
                "total_pret": total_pret,
                "total_versement": total_versement,
                "balance": balance,
            })

        # Totaux globaux
        montant_pret = sum(c["total_pret"] for c in produits_data)
        montant_versement = sum(c["total_versement"] for c in produits_data)
        balance_total = sum(c["balance"] for c in produits_data)

        # Format
        def formater(montant):
            return "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique = InfoBoutique.objects.first()
        context = {
            'listes': produits_data,
            'montantPret': formater(montant_pret),
            'montantVersement': formater(montant_versement),
            'balance': formater(balance_total),
            'boutique': infoBoutique,
        }

        return generate_pdf_response_vrais("CommercialSoft/pdfEtatSituationClient.html", context)

    return HttpResponse("Méthode non autorisée", status=405)





def get_reste_client(request, id):
    total_pret = PretClient.objects.filter(client=id).aggregate(total=Sum('montant'))['total'] or 0
    total_versement = VersementClient.objects.filter(client=id).aggregate(total=Sum('montant'))['total'] or 0
    balance = total_pret - total_versement

    return JsonResponse({
        'total_pret': total_pret,
        'total_versement': total_versement,
        'balance': balance
    })







#--------------------------liste des Versement des fournisseur -----------------------
# Exemple d'utilisation
def pdf_etat_situation_fournisseur(request):
    if request.method =="POST":
        fournisseurId= request.POST.get('idFournisseur')
        fournisseurId=int(fournisseurId)
        
        fournisseurs=Fournisseur.objects.filter()

        # Filtrer par catégorie si elle est fournie
        if fournisseurId:
            try:
                fournisseurs = Fournisseur.objects.filter(id=fournisseurId)
            except Fournisseur.DoesNotExist:
                return JsonResponse({"error": "fournisseur introuvable"}, status=404)

        # Construire la réponse JSON
        montantPret=0
        montantVersement=0
        balance=0
        produits_data = [
            {
                "id": fournisseur.id,
                "nom": fournisseur.nom,
                "telephone": fournisseur.telephone,
                "adresse": fournisseur.adresse,
                "total_pret": fournisseur.detteFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0,
                "total_versement": fournisseur.versementFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0,
                "balance": (fournisseur.detteFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0) - 
                           (fournisseur.versementFournisseur.aggregate(Sum('montant'))['montant__sum'] or 0),
            }
            for fournisseur in fournisseurs
        ]

        montantPret = sum(fournisseur["total_pret"] for fournisseur in produits_data)
        montantVersement = sum(fournisseur["total_versement"] for fournisseur in produits_data)
        balance = sum(fournisseur["balance"] for fournisseur in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montantPret_formate = "{:,.0f}".format(montantPret).replace(",", " ")
        montantVersement_formate = "{:,.0f}".format(montantVersement).replace(",", " ")
        balance_formate = "{:,.0f}".format(balance).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montantPret': montantPret_formate,'montantVersement':montantVersement_formate, 'balance':balance_formate,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatSituationFournisseur.html", context)

    return HttpResponse("Méthode non autorisée", status=405)






#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_situation_boutique(request):
    if request.method =="POST":
        typePrix= request.POST.get('typePrix')

        # Mapping des types de prix aux attributs correspondants
        prix_mapping = {
            "achat": "prixAchat",
            "enGros": "prixEnGros",  # Correction ici
            "detail": "prixDetail"
        }

        # Vérification de la validité du typePrix
        if typePrix not in prix_mapping:
            return JsonResponse({"error": "Type de prix invalide"}, status=400)

        # Récupération des produits
        produits = Produit.objects.all()
        
        # Construction des données de réponse
        produits_data = [
            {
                "id": produit.id,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "prix": getattr(produit, prix_mapping[typePrix]),  # Accès dynamique à l'attribut
                "montant": produit.quantite * getattr(produit, prix_mapping[typePrix]),
                "montantAchat":produit.quantite*produit.prixAchat,
            }
            for produit in produits
        ]

        montantTotal = sum(produit["montant"] for produit in produits_data)
        montantAchat = sum(produit["montantAchat"] for produit in produits_data)
        benefice=montantTotal-montantAchat
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montantTotal).replace(",", " ")
        benefice_formate = "{:,.0f}".format(benefice).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'benefice':benefice_formate,'boutique':infoBoutique}
        
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatSituationBoutique.html", context)

    return HttpResponse("Méthode non autorisée", status=405)






#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_produit_perime(request):
    if request.method =="POST":
        
        aujourdhui = timezone.now().date()
        produits = Produit.objects.filter(datePeremption__lt=aujourdhui)
        
        # Construction des données de réponse
        produits_data = [
            {
                "id": produit.id,
                "codebare":produit.codebare,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "datePeremption": produit.datePeremption,  # Accès dynamique à l'attribut
                "seuil": produit.seuil,
            }
            for produit in produits
        ]

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data,'boutique':infoBoutique}
        
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatProduitPerime.html", context)

    return HttpResponse("Méthode non autorisée", status=405)





#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_produit_rupture(request):
    if request.method =="POST":
        
        produits=Produit.objects.filter(quantite__lte=F('seuil'))
        
        # Construction des données de réponse
        produits_data = [
            {
                "id": produit.id,
                "codebare":produit.codebare,
                "libelle": produit.libelle,
                "quantite": produit.quantite,
                "seuil": produit.seuil,
                "datePeremption": produit.datePeremption,  # Accès dynamique à l'attribut
                "prixDetail": produit.prixDetail,
            }
            for produit in produits
        ]

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data,'boutique':infoBoutique}
        
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatProduitRupture.html", context)

    return HttpResponse("Méthode non autorisée", status=405)







#--------------------------liste des produits livrer -----------------------
# Exemple d'utilisation
def pdf_etat_pretClient(request):
    if request.method =="POST":
        dateDebut= request.POST.get('dateDebut')
        dateFin= request.POST.get('dateFin')
        clientId= request.POST.get('idClient')

        prets=PretClient.objects.filter(date__gte=dateDebut, date__lte=dateFin)

        # Filtrer par catégorie si elle est fournie
        if clientId:
            try:
                client = Client.objects.get(id=clientId)
                prets=PretClient.objects.filter(client=client,date__gte=dateDebut, date__lte=dateFin)
            except Client.DoesNotExist:
                return JsonResponse({"error": "Client introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": pret.id,
                "client": pret.client.nom,
                "montant": pret.montant,
                "date": pret.date,
                "dateEcheance": pret.dateEcheance,
                "user": pret.user.first_name +" "+ pret.user.last_name
            }
            for pret in prets
        ]

        montant = sum(pret["montant"] for pret in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
        
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatPretClient.html", context)

    return HttpResponse("Méthode non autorisée", status=405)







#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_versementGerant(request):
    if request.method =="POST":
        dateDebut= request.POST.get('dateDebut')
        dateFin= request.POST.get('dateFin')
        gerantId= request.POST.get('idGerant')

        versements=VersementGerant.objects.filter(date__gte=dateDebut, date__lte=dateFin)

        # Filtrer par catégorie si elle est fournie
        if gerantId:
            try:
                user = User.objects.get(id=gerantId)
                versements=VersementGerant.objects.filter(user=user,date__gte=dateDebut, date__lte=dateFin)
            except VersementGerant.DoesNotExist:
                return JsonResponse({"error": "Client introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": versement.id,
                "montant": versement.montant,
                "date": versement.date,
                "user":versement.user.first_name+" "+versement.user.last_name
            }
            for versement in versements
        ]

        montant = sum(versement["montant"] for versement in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        infoBoutique=InfoBoutique.objects.first()
        context = {'listes': produits_data, 'montant': montant_formate,'boutique':infoBoutique}
        return generate_pdf_response_vrais("CommercialSoft/pdfEtatVersementGerant.html", context)

    return HttpResponse("Méthode non autorisée", status=405)






#--------------------------liste des Versement des client -----------------------
# Exemple d'utilisation
def pdf_etat_situation_vente(request):
    try:
        if request.method =="POST":
            idProduit = request.POST.get('idProduit')
            dateDebut = request.POST.get("dateDebut")
            dateFin = request.POST.get("dateFin")

            # Récupérer les ventes
            produits_infos = []

            if idProduit != "":
                try:
                    produit = Produit.objects.get(id=idProduit)

                    # Calculer quantités pour ce produit
                    entree = LivraisonProduit.objects.filter(produit=produit)
                    sortie = CommandeProduit.objects.filter(produit=produit)

                    if dateDebut:
                        entree = entree.filter(livraison__date__gte=dateDebut)
                        sortie = sortie.filter(date__gte=dateDebut)
                    if dateFin:
                        entree = entree.filter(livraison__date__lte=dateFin)
                        sortie = sortie.filter(date__lte=dateFin)

                    quantite_entree = entree.aggregate(total=Sum("quantite"))["total"] or 0
                    quantite_sortie = sortie.aggregate(total=Sum("quantite"))["total"] or 0
                    stock = produit.quantite or 0

                    produits_infos.append({
                        "id": produit.id,
                        "libelle": produit.libelle,
                        "quantite_entree": quantite_entree,
                        "quantite_sortie": quantite_sortie,
                        "stock": stock
                    })

                except Produit.DoesNotExist:
                    return JsonResponse({"error": "Produit introuvable"}, status=404)

            else:
                # Parcourir tous les produits
                produits = Produit.objects.all()
                for produit in produits:
                    entree = LivraisonProduit.objects.filter(produit=produit)
                    sortie = CommandeProduit.objects.filter(produit=produit)

                    if dateDebut:
                        entree = entree.filter(livraison__date__gte=dateDebut)
                        sortie = sortie.filter(date__gte=dateDebut)
                    if dateFin:
                        entree = entree.filter(livraison__date__lte=dateFin)
                        sortie = sortie.filter(date__lte=dateFin)

                    quantite_entree = entree.aggregate(total=Sum("quantite"))["total"] or 0
                    quantite_sortie = sortie.aggregate(total=Sum("quantite"))["total"] or 0
                    stock = produit.quantite or 0

                    produits_infos.append({
                        "id": produit.id,
                        "libelle": produit.libelle,
                        "quantite_entree": quantite_entree,
                        "quantite_sortie": quantite_sortie,
                        "stock": stock
                    })

            infoBoutique=InfoBoutique.objects.first()
            context = {'listes': produits_infos, 'boutique':infoBoutique}
            return generate_pdf_response_vrais("CommercialSoft/pdfEtatSituationVente.html", context)
    except Exception as e:
        print("Erreur ", e)
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
        
    return HttpResponse("Méthode non autorisée", status=405)




def pdf_etat_reception_produit(request):
    if request.method == "POST":
        try:
            idFournisseur = request.POST.get('idFournisseur')
            idProduit = request.POST.get('idProduit')
            dateDebut = request.POST.get("dateDebut")
            dateFin = request.POST.get("dateFin")

            # Préparation de la requête avec select_related pour optimiser
            livraisons_produits = LivraisonProduit.objects.select_related('livraison', 'produit', 'livraison__fournisseur')

            # Application des filtres si fournis
            if dateDebut:
                livraisons_produits = livraisons_produits.filter(livraison__date__gte=dateDebut)
            if dateFin:
                livraisons_produits = livraisons_produits.filter(livraison__date__lte=dateFin)
            if idFournisseur:
                livraisons_produits = livraisons_produits.filter(livraison__fournisseur__id=idFournisseur)
            if idProduit:
                livraisons_produits = livraisons_produits.filter(produit__id=idProduit)

            # Construction de la réponse
            resultats = []
            for lp in livraisons_produits:
                resultats.append({
                    "id": lp.produit.id,
                    "fournisseur": lp.livraison.fournisseur.nom,
                    "produit": lp.produit.libelle,
                    "quantite": lp.quantite,
                    "prix": lp.prix,
                    "montant":lp.prix*lp.quantite,
                    "date_livraison": lp.livraison.date.strftime("%Y-%m-%d"),
                })

            infoBoutique=InfoBoutique.objects.first()
            context = {'listes': resultats, 'boutique':infoBoutique}
            return generate_pdf_response_vrais("CommercialSoft/pdfReceptionProduit.html", context)

        except Exception as e:
            print("Erreur ", e)
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return HttpResponse("Méthode non autorisée", status=405)




@user_passes_test(est_administrateur)
@login_required
def caisse(request):
    # solde fournisseur
    dette_fournisseur = DetteFournisseur.objects.aggregate(total=Sum('montant'))['total'] or 0
    payement_fournisseur=VersementFournisseur.objects.aggregate(total=Sum('montant'))['total'] or 0
    solde_fournisseur=dette_fournisseur-payement_fournisseur

    # solde client
    pret_client=PretClient.objects.aggregate(total=Sum('montant'))['total'] or 0
    versement_client=VersementClient.objects.aggregate(total=Sum('montant'))['total'] or 0
    solde_client=pret_client-versement_client

    # depense
    #depense=Depense.objects.aggregate(total=Sum(F('quantite') * F('prix')))['total'] or 0

    #versement gerant
    versement_gerant=VersementGerant.objects.aggregate(total=Sum('montant'))['total'] or 0

    # stock
    # valeur_stock = Produit.objects.aggregate(total=Sum(F('quantite') * F('prixAchat')))['total'] or 0
    valeur_stock = Produit.objects.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('quantite') * F('prixAchat'),
                output_field=DecimalField(max_digits=38, decimal_places=2)
            )
        )
    )['total'] or 0


    # total client et stock
    client_stock=valeur_stock + solde_client
    solde_general=client_stock+versement_gerant
    solde_pdg=solde_general-solde_fournisseur

    return render(request, 'CommercialSoft/caisse.html',{
        'stock': separateur(valeur_stock),
        'dette_client': separateur(solde_client),
        'client_stock': separateur(client_stock),
        'banque': separateur(versement_gerant),
        'solde_general':separateur(solde_general),
        'solde_fournisseur': separateur(solde_fournisseur),
        'solde_pdg': separateur(solde_pdg)
    })






@csrf_exempt
@login_required
def enregistrer_retours(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            with transaction.atomic():
                for item in data['retours']:
                    produit = Produit.objects.select_for_update().get(id=item['produit_id'])
                    
                    # Mise à jour du stock
                    print(item['quantite'], type(item['quantite']))
                    qte = int(item.get('quantite') or 0)
                    produit.quantite += qte
                    produit.save()

                    # Création du retour
                    Retour.objects.create(
                        produit=produit,
                        quantite=item['quantite'],
                        date=timezone.now().date(),
                        user=request.user,
                        prix=item['prix']
                    )

            messages.success(request, "Retours enregistrés avec succès.")
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})





@login_required
def recherche_retours(request):
    if request.method == "POST":
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")

        retours=Retour.objects.all()

        if dateDebut and dateFin:
            retours = Retour.objects.filter(date__gte=dateDebut, date__lte=dateFin)  # Récupérer tous les produits par défaut

       
        # Construire la réponse JSON
        produits_data = [
            {
                "id":retour.id,
                "produit": retour.produit.libelle,
                "quantite": retour.quantite,
                "prix": retour.prix,
                "date": retour.date,
                "montant": retour.prix * retour.quantite,
                "user": f"{retour.user.first_name} {retour.user.last_name}",
            }
            for retour in retours
        ]
        
        return JsonResponse({"livraison": produits_data})

    return JsonResponse({"error": "Requête invalide"}, status=400)




 # Example for Patient Views
@login_required
def retour_delete(request, pk):
    retour = get_object_or_404(Retour, pk=pk)
    try:
        with transaction.atomic():
            produit=retour.produit
            produit.quantite +=retour.quantite
            produit.save()
            retour.delete()
        messages.success(request, "Retour supprimé avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce retour est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('retours')




@login_required
def retours(request):
    users = User.objects.all()
    return render(request, 'CommercialSoft/listeRetour.html',{'users':users})






"""
@csrf_exempt
def pdf_facture_proforma(request):
    if request.method == "POST":
        try:
            data_json = request.POST.get('data')
            donnees = json.loads(data_json)

            infoBoutique = InfoBoutique.objects.first()

            # Calcul du total
            total = sum(item.get("montant", 0) for item in donnees)
            total_formate = "{:,}".format(total).replace(",", " ")

            context = {
                'listes': donnees,
                'boutique': infoBoutique,
                'total': total_formate,
                'date': timezone.now().strftime("%Y-%m-%d"),
            }

            return generate_pdf_response_vrais("CommercialSoft/pdfFactureProforma.html", context)

        except Exception as e:
            print("Erreur", e)
            return HttpResponse("Erreur serveur : " + str(e), status=500)

    return HttpResponse("Méthode non autorisée", status=405)
"""





def pdf_facture_proforma(request):
    if request.method == "POST":
        try:
            data_json = request.POST.get('data')
            data = json.loads(data_json)

            infoBoutique = InfoBoutique.objects.first()

            # Liste des articles
            donnees = data.get("produits", [])

            # Calcul du total brut
            total = sum(item.get("montant", 0) for item in donnees)

            # Récupération de la remise (par défaut 0)
            remise = data.get("remise", 0)

            idClient = data.get("clientId", 0)
            

            # Calcul du total net après remise
            total_net = total - remise
            if total_net < 0:
                total_net = 0  # éviter total négatif

            # Formatage
            total_formate = "{:,}".format(total).replace(",", " ")
            remise_formate = "{:,}".format(remise).replace(",", " ")
            total_net_formate = "{:,}".format(total_net).replace(",", " ")

            context = {
                'listes': donnees,
                'boutique': infoBoutique,
                'total': total_formate,
                'remise': remise_formate,
                'total_net': total_net_formate,
                'date': timezone.now().strftime("%Y-%m-%d"),
                'client': Client.objects.get(id=idClient).nom if idClient else "",
                'numero_client': Client.objects.get(id=idClient).telephone if idClient else "",
            }

            return generate_pdf_response_vrais("CommercialSoft/pdfFactureProforma.html", context)

        except Exception as e:
            print("Erreur", e)
            return HttpResponse("Erreur serveur : " + str(e), status=500)

    return HttpResponse("Méthode non autorisée", status=405)






def pdf_facture_proforma_2(request, commande_id):
    try:
        # ✅ 1️⃣ Récupération de la commande
        commande = get_object_or_404(Commande, id=commande_id)

        # ✅ 2️⃣ Informations de la boutique
        infoBoutique = InfoBoutique.objects.first()

        # ✅ 3️⃣ Liste des lignes de la commande
        lignes = CommandeProduit.objects.filter(commande=commande)

        # ✅ 4️⃣ Conversion en format utilisable par le template
        donnees = []
        for ligne in lignes:
            donnees.append({
                "produit": ligne.produit.libelle,
                "quantite": ligne.quantite,
                "prix": ligne.prix,
                "montant": ligne.quantite*ligne.prix
            })

        # ✅ 5️⃣ Calculs des totaux
        total = sum(l.quantite*l.prix for l in lignes)
        remise = commande.remise if hasattr(commande, 'remise') else 0
        total_net = total - remise if total > remise else 0

        # ✅ 6️⃣ Formatage des montants
        total_formate = "{:,}".format(total).replace(",", " ")
        remise_formate = "{:,}".format(remise).replace(",", " ")
        total_net_formate = "{:,}".format(total_net).replace(",", " ")

        # ✅ 7️⃣ Client
        client = commande.client if hasattr(commande, 'client') else None

        # ✅ 8️⃣ Contexte pour le template
        context = {
            'id':commande.id if commande.id else "",
            'listes': donnees,
            'boutique': infoBoutique,
            'total': total_formate,
            'remise': remise_formate,
            'total_net': total_net_formate,
            'date': commande.date.strftime("%Y-%m-%d") if hasattr(commande, 'date') else timezone.now().strftime("%Y-%m-%d"),
            'client': client.nom if client else "",
            'numero_client': client.telephone if client else "",
        }

        # ✅ 9️⃣ Génération du PDF
        return generate_pdf_response_vrais("CommercialSoft/pdfFactureProforma.html", context)

    except Exception as e:
        print("❌ Erreur :", e)
        return HttpResponse("Erreur serveur : " + str(e), status=500)








# views.py
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UploadFileForm
from .models import Societe, Client, Produit, Categorie

def import_excel_view(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            fichier_excel = request.FILES["fichier"]
            table = form.cleaned_data["table"]

            try:
                df = pd.read_excel(fichier_excel)

                if table == "societe":
                    for _, row in df.iterrows():
                        Societe.objects.update_or_create(
                            nom=row["nom"],
                            defaults={
                                "adresse": row.get("adresse", None),
                                "telephone": row.get("telephone", None),
                            }
                        )

                elif table == "client":
                    for _, row in df.iterrows():
                        societe_obj = None
                        if "societe" in df.columns and not pd.isna(row["societe"]):
                            societe_obj, _ = Societe.objects.get_or_create(nom=row["societe"])

                        Client.objects.update_or_create(
                            nom=row["nom"],
                            defaults={
                                "societe": societe_obj,
                                "telephone": row.get("telephone", None),
                                "adresse": row.get("adresse", None),
                                "email": row.get("email", None),
                                "matricule": row.get("matricule", None),
                                "pourcentage": row.get("pourcentage", 0),
                                "detteMaximale": row.get("detteMaximale", 0),
                            }
                        )

                elif table == "produit":
                    for _, row in df.iterrows():
                        categorie_obj = None
                        if "categorie" in df.columns and not pd.isna(row["categorie"]):
                            categorie_obj, _ = Categorie.objects.get_or_create(nom=row["categorie"])

                        Produit.objects.update_or_create(
                            libelle=row["libelle"],
                            defaults={
                                "codebare": row.get("codebare", None),
                                "categorie": categorie_obj,
                                "quantite": row.get("quantite", 0),
                                "prixAchat": row.get("prixAchat", 0),
                                "prixEnGros": row.get("prixEnGros", 0),
                                "prixDetail": row.get("prixDetail", 0),
                                "date": row.get("date", None),
                                "datePeremption": row.get("datePeremption", None),
                                "seuil": row.get("seuil", 0),
                                "commentaire": row.get("commentaire", None),
                                "quantiteTotal": row.get("quantiteTotal", 0),
                            }
                        )

                messages.success(request, f"✅ Import réussi dans la table {table}")
                return redirect("chargeDonnee")

            except Exception as e:
                messages.error(request, f"❌ Erreur lors de l’import : {e}")

    else:
        form = UploadFileForm()

    return render(request, "CommercialSoft/import_excel.html", {"form": form})






#---------- Gestion horconnexion ---------------------------
def api_produits(request):
    produits = list(Produit.objects.values("id", "codebare", "categorie","libelle", "quantite", "prixAchat", "prixEnGros", "prixDetail", "date", "datePeremption", "seuil", "commentaire", "quantiteTotal"))
    clients = list(Client.objects.values("id", "nom", "telephone", "adresse", "email", "matricule", "pourcentage", "detteMaximale"))
    return JsonResponse({
        "produits": produits,
        "clients": clients,
    }, safe=False)



# ---- Service worker à la racine ----
# CommercialSoft/views.py
from django.http import HttpResponse
from django.template import loader

def service_worker(request):
    """
    Retourne le Service Worker à la racine (/serviceworker.js)
    """
    template = loader.get_template("CommercialSoft/serviceworker.js")
    return HttpResponse(template.render(), content_type="application/javascript")





def offline(request):
    return render(request, "CommercialSoft/offline.html")






from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
"""
@csrf_exempt  # à remplacer plus tard par un décorateur avec authentification/token
def sync_ventes(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        ventes = data.get("ventes", [])

        for vente in ventes:
            # Créer une Commande
            user_id=int(vente.get("user")) if vente.get("user") else request.user.id
            client_id = vente.get("client")
            if vente.get("typePayement") == "Pret":
                client =Client.objects.get(id=int(client_id))
            else:
                client = None
            
            montant_sans_remise = vente.get("montant", 0) + vente.get("remise", 0)
            commande = Commande.objects.create(
                user=User.objects.get(id=user_id),
                client =  client,
                montant=montant_sans_remise,
                remise=vente.get("remise", 0),
                date=vente.get("date", timezone.now().date()),
                typeVente=vente.get("typeVente"),
                typePayement=vente.get("typePayement", "Espece"),
                montantAchat=0,
            )
            
            montant_achat = 0

            for item in vente.get("lignes", []):
                produit = Produit.objects.get(id=int(item["produit_id"]))
                quantite = int(item["quantite"])
                prix = int(item["prix"])

                # décrémenter le stock
                produit.quantite -= quantite
                produit.save()

                CommandeProduit.objects.create(
                    commande=commande,
                    produit=produit,
                    quantite=quantite,
                    prix=prix,
                    date=vente.get("date", timezone.now().date()),
                )

                montant_achat += produit.prixAchat * quantite
            
            commande.montantAchat = montant_achat
            commande.save()

            
            
            if vente.get("typePayement") == "Pret":
                montant_pret = vente.get("montant")
                if montant_pret > 0 and client_id:
                    PretClient.objects.create(
                        client=client,
                        montant=montant_pret,
                        date=vente.get("date", timezone.now().date()),
                        dateEcheance=vente.get("dateEcheance", timezone.now().date()),
                        commande=commande,
                        user=User.objects.get(id=user_id),
                    )
        return JsonResponse({"success": True, "message": "Ventes synchronisées"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

from CommercialSoft.models import Commande, CommandeProduit, Produit, Client, PretClient

User = get_user_model()  # ✅ Récupère ton CustomUser

@csrf_exempt
def sync_ventes(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)

    try:
        vente = json.loads(request.body)  # une seule vente envoyée
        if not vente:
            return JsonResponse({"success": False, "message": "vente deja synchronisé"}, status=400)

        user_id=int(vente.get("user")) if vente.get("user") else request.user.id
        id_local = vente.get("id_local")
        client_id = vente.get("client")
        if vente.get("typePayement") == "Pret":
            client =Client.objects.get(id=int(client_id))
        else:
            client = None

        if Commande.objects.filter(client_uid=id_local).exists():
            return JsonResponse({"success": True, "error": "Aucune donnée reçue"}, status=400)
        
        montant_sans_remise = vente.get("montant", 0) + vente.get("remise", 0)
        commande = Commande.objects.create(
            user=User.objects.get(id=user_id),
            client =  client,
            montant=montant_sans_remise,
            remise=vente.get("remise", 0),
            date = vente.get("date") or timezone.now().date(),
            #date = date(2025, 10, 14),  # Pour test
            typeVente=vente.get("typeVente"),
            typePayement=vente.get("typePayement", "Espece"),
            montantAchat=0,
            client_uid=id_local,  # Stocke l'ID local du client (si nécessaire pour le suivi
        )
        
        montant_achat = 0

        for item in vente.get("lignes", []):
            produit = Produit.objects.get(id=int(item["produit_id"]))
            quantite = int(item["quantite"])
            prix = int(item["prix"])

            # décrémenter le stock
            produit.quantite -= quantite
            produit.save()

            CommandeProduit.objects.create(
                commande=commande,
                produit=produit,
                quantite=quantite,
                prix=prix,
                date=vente.get("date", timezone.now().date()),
            )

            montant_achat += produit.prixAchat * quantite
        
        commande.montantAchat = montant_achat
        commande.save()

        
        
        if vente.get("typePayement") == "Pret":
            montant_pret = vente.get("montant")
            if montant_pret > 0 and client_id:
                PretClient.objects.create(
                    client=client,
                    montant=montant_pret,
                    date=vente.get("date", timezone.now().date()),
                    dateEcheance=vente.get("dateEcheance", timezone.now().date()),
                    commande=commande,
                    user=User.objects.get(id=user_id),
                )

        return JsonResponse({"success": True, "message": "✅ Vente synchronisée avec succès !"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
