from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from .forms import LoginForm, FournisseurForm, CategorieForm, ProduitForm, LivraisonForm, LivraisonProduitFormSet, CommandeForm, CommandeProduitFormSet, LivraisonProduitForm, CategorieDepenseForm, DepenseForm, VersementClientForm, pretClientForm, clientForm, societeForm, DetteFournisseurForm, VersementFournisseurForm, detteClientForm, VersementGerantForm
from .models import Fournisseur, Categorie, Produit, Livraison, LivraisonProduit, Commande, CommandeProduit, Categorie_Depense, Depense, VersementClient, PretClient, Client, Societe, DetteFournisseur, VersementFournisseur, VersementGerant
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.timezone import now, localdate
from django.db import IntegrityError
from django.http import JsonResponse
from django.db import transaction
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Sum, F
from django.contrib.auth import get_user_model
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
    return render(request, 'CommercialSoft/dashboard.html',{'nom_agent':request.user.username,'numero_user':request.user.id})




# examen Views
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
    
    produit = Produit.objects.all()
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
def reception_create(request):
    if request.method == 'POST':
        livraison_form = LivraisonForm(request.POST)
        formset = LivraisonProduitFormSet(request.POST)

        if livraison_form.is_valid() and formset.is_valid():
            with transaction.atomic():  # Ensure database integrity
                try:
                    # Save Livraison
                    livraison = livraison_form.save()
                    # Process each form in the formset
                    for form in formset:
                        if not (form.cleaned_data.get('produit') and form.cleaned_data.get('quantite')):  # Skip empty forms
                            continue
                        livraison_produit = form.save(commit=False)
                        livraison_produit.livraison = livraison

                        produit = livraison_produit.produit
                        produit.quantiteTotal += livraison_produit.quantite
                        produit.prixAchat = livraison_produit.prix
                        produit.quantite +=livraison_produit.quantite
                        produit.prixDetail=livraison_produit.prixDetail

                        produit.save()

                        livraison_produit.save()
                    messages.success(request,"Enregistrement reussi")
                    return redirect('commerce_reception')
                except Exception as e:
                    # Handle exceptions (log error, notify user, etc.)
                    messages.error(request,f"Error processing livraison: {e}")
                # Optionally add an error message to the user
        else:
            # Print form errors for debugging
            messages.error(request,"Livraison form errors:", livraison_form.errors)
            for error in formset.errors:
                if error:  # Vérifie si l'erreur existe
                    messages.error(request, f"Erreur dans un formulaire : {error}")
    
    livraison_form = LivraisonForm()
    formset = LivraisonProduitFormSet()

    produits = Produit.objects.all()
    return render(request, 'CommercialSoft/reception.html', {
        'livraison_form': livraison_form,
        'formset': formset,
        'listes': produits,
    })





@login_required
def reception_delete(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    try:
        livraison.delete()
        messages.success(request, "livraison supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette livraison est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('produitLivrer')




@login_required
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
def produit_livrer_delete(request, pk):
    livraisonP = get_object_or_404(LivraisonProduit, pk=pk)
    try:
        livraisonP.delete()
        messages.success(request, "Produit supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette produit est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_detailReception', livraisonP.livraison.id)




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
        data = {"success": False}
    
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
        if categorieId:
            try:
                cat = Categorie.objects.get(id=categorieId)
                produits = produits.filter(categorie=cat)
            except Categorie.DoesNotExist:
                return JsonResponse({"error": "Catégorie introuvable"}, status=404)

        # Filtrer par produit si fourni
        if produitId:
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
            messages.error(request,"commande form errors : ", commande_form.errors)
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

        return JsonResponse({"vente": produits_data})

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





@user_passes_test(est_administrateur, est_gestionnaire)
@login_required
def vente_delete(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    try:
        commande.delete()
        messages.success(request, "vente supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Cette vente est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_produitVendu')




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
            commande.save()
            return JsonResponse({"success": True, "message": "Produit supprimé avec succès !"})
        except IntegrityError:
            return JsonResponse({"success": False, "message": "Erreur: Impossible de supprimer ce produit."}, status=400)





@login_required
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
            form.save()  # Sauvegarder après modification
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






# examen Views
@login_required
def versementClient_list_create(request):
    if request.method == "POST":
        form = VersementClientForm(request.POST)
        if form.is_valid():
            form.save()  # Sauvegarder après modification
            messages.success(request, "Versement créée avec succès !")
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
def versementClient_delete(request, pk):
    versement = get_object_or_404(VersementClient, pk=pk)
    try:
        versement.delete()
        messages.success(request, "versement supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce versement est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_versementClient')









# examen Views
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
def recherche_pretClient(request):
    if request.method == "POST":
        numero = request.POST.get('idClient', '0').strip()  # Récupérer le numéro envoyé
        dateDebut = request.POST.get("dateDebut")
        dateFin = request.POST.get("dateFin")
        if numero :  # Si un numéro est saisi
            client = Client.objects.get(id=numero)
            pretClients=PretClient.objects.filter(client=client,date__gte=dateDebut, date__lte=dateFin)
        else:  # Sinon, afficher les patients du jour
            pretClients=PretClient.objects.filter(date__gte=dateDebut, date__lte=dateFin)
            
        # Construire une réponse JSON
        patients_data = [
            {
                "id": pret.id,
                "client": pret.client.nom,
                "montant":pret.montant,
                "date": pret.date,
                "dateEcheance":pret.dateEcheance,
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
def versementFournisseur_list(request):
    fournisseur=VersementFournisseur()
    return render(request, 'CommercialSoft/listeDepense.html',{'form':fournisseur})





@login_required
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
def societe_delete(request, pk):
    societe = get_object_or_404(Societe, pk=pk)
    try:
        societe.delete()
        messages.success(request, "societe supprimée avec succès!")
    except IntegrityError:
        messages.error(request, "Erreur: Ce societe est liée à d'autres entités et ne peut pas être supprimée.")
    return redirect('commerce_societe')




@login_required
def bilan(request):
    users = User.objects.all()
    return render(request, 'CommercialSoft/bilan.html',{'users':users})




@login_required
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

        #pret reclamer
        pretReclamer = VersementClient.objects.filter(**filtre)
        depense = Depense.objects.filter(**filtre)

        # Vérifier si idUser est valide (non 0 et correspondant à un utilisateur existant)
        if idUser and idUser != "0":
            try:
                user = User.objects.get(id=idUser)
                filtre["user"] = user
            except User.DoesNotExist:
                return JsonResponse({"error": "Utilisateur introuvable"}, status=404)

        # Appliquer le filtre à la requête
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

        caisse=total_net_vente+total_pretReclamer-total_pret-total_depense or 0

        # Retourner la réponse JSON
        return JsonResponse({
            "totalVente": total_net_vente,
            "totalPretReclame": total_pretReclamer,
            "totalPret": total_pret,
            "totalDepense":total_depense,
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
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
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
    context = {'listes': produits,'total':total_formatte,'net':net_formatte,'remise':commande.remise}
    
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










from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse

def generate_pdf_response_vrais(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="produit_disponible.pdf"'
        return response
    return HttpResponse("Erreur lors de la génération du PDF", status=500)



#--------------------------liste des produits disponible -----------------------
# Exemple d'utilisation
def pdf_Produit_disponible(request):
    if request.method =="POST":
        categorieId = request.POST.get('idCategorie')
        produitId = request.POST.get("produitId")
        # Données contextuelles pour le template HTML (vous pouvez ajuster cela)
        produits = Produit.objects.all()  # Récupérer tous les produits par défaut

        # Filtrer par catégorie si elle est fournie
        if categorieId:
            try:
                cat = Categorie.objects.get(id=categorieId)
                produits = produits.filter(categorie=cat)
            except Categorie.DoesNotExist:
                return JsonResponse({"error": "Catégorie introuvable"}, status=404)

        # Filtrer par produit si fourni
        if produitId:
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
        context = {'listes': produits_data}
        
        return generate_pdf_response_vrais("commercialSoft/pdfProduitDisponible.html", context)













    


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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfProduitLivrer.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'produit_livre.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response




#--------------------------liste des produits livrer -----------------------
# Exemple d'utilisation

def pdf_etat_depense(request):
    if request.method =="POST":
        dateDebut= request.POST.get('dateDebut')
        dateFin= request.POST.get('dateFin')
        categorieId= request.POST.get('idCategorie')

        depenses=Depense.objects.filter(date__gte=dateDebut, date__lte=dateFin)

        # Filtrer par catégorie si elle est fournie
        if categorieId:
            try:
                cat = Categorie_Depense.objects.get(id=categorieId)
                depenses=Depense.objects.filter(categorie=cat,date__gte=dateDebut, date__lte=dateFin)
            except Categorie_Depense.DoesNotExist:
                return JsonResponse({"error": "Catégorie introuvable"}, status=404)

        # Construire la réponse JSON
        montant=0
        produits_data = [
            {
                "code": depense.id,
                "intitule": depense.intitule,
                "quantite": depense.quantite,
                "prix": depense.prix,
                "date": depense.date,
                "categorie":depense.categorie,
                "montant": depense.quantite*depense.prix,
            }
            for depense in depenses
        ]

        montant = sum(depense["montant"] for depense in produits_data)
        # Formatage avec séparateur de milliers (ex: 1 234 567)
        montant_formate = "{:,.0f}".format(montant).replace(",", " ")

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatDepense.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_depense.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatVersementClient.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_versementClient.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatVersementFournisseur.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_versementFournisseur.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatClient.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_client.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
    return HttpResponse("Méthode non autorisée", status=405)




#--------------------------liste des Versement des client -----------------------

def pdf_etat_situation_client(request):
    if request.method == "POST":
        id_client_str = request.POST.get('idClient')

        clients = Client.objects.all()  # Par défaut, on récupère tous les clients

        if id_client_str:  # Si un ID est fourni
            try:
                id_client = int(id_client_str)
                clients = Client.objects.filter(id=id_client)

                if not clients.exists():
                    return JsonResponse({"error": "Client introuvable"}, status=404)

            except ValueError:
                return JsonResponse({"error": "ID du client invalide"}, status=400)

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

        # Calcul des totaux globaux
        montant_pret = sum(c["total_pret"] for c in produits_data)
        montant_versement = sum(c["total_versement"] for c in produits_data)
        balance_total = sum(c["balance"] for c in produits_data)

        # Formatage des montants
        def formater(montant):
            return "{:,.0f}".format(montant).replace(",", " ")

        context = {
            'listes': produits_data,
            'montantPret': formater(montant_pret),
            'montantVersement': formater(montant_versement),
            'balance': formater(balance_total),
        }

        # Génération du PDF
        template_name = 'commercialSoft/pdfEtatSituationClient.html'
        output_filename = 'situation_client.pdf'
        generate_pdf_from_template(template_name, context, output_filename)

        with open(output_filename, 'rb') as pdf_file:
            return HttpResponse(pdf_file.read(), content_type='application/pdf')

    return HttpResponse("Méthode non autorisée", status=405)







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

        context = {'listes': produits_data, 'montantPret': montantPret_formate,'montantVersement':montantVersement_formate, 'balance':balance_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatSituationFournisseur.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'situation_fournisseur.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate,'benefice':benefice_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatSituationBoutique.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'situation_boutique.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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


        context = {'listes': produits_data}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatProduitPerime.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'produit_perime.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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


        context = {'listes': produits_data}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatProduitRupture.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'produit_rupture.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatPretClient.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_pretClient.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
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

        context = {'listes': produits_data, 'montant': montant_formate}
        
        # Chemin vers le fichier HTML dans le répertoire templates
        template_name = 'commercialSoft/pdfEtatVersementGerant.html'  # Chemin relatif à partir du répertoire templates
        output_filename = 'etat_versementGerant.pdf'  # Nom du fichier PDF généré
        
        # Générer le PDF à partir du template
        generate_pdf_from_template(template_name, context, output_filename)

        # Renvoyer le fichier PDF comme réponse HTTP
        with open(output_filename, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{output_filename}"'
            return response
    return HttpResponse("Méthode non autorisée", status=405)
