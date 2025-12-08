from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns=[
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('register/', include(('accounts.urls', 'register'), namespace='accounts')),

    path('dashboard/', views.dashboard, name="commerce_dashboard"),
    path('fournisseur/', views.fournisseur_list_create,name="commerce_fournisseur"),    
    path('fournisseur/modification/<int:pk>/', views.fournisseur_edit,name="commerce_fournisseurEdit"),
    path('fournisseur/suppression/<int:pk>/', views.fournisseur_delete,name="commerce_fournisseurDelete"),
    path('commerce/fournisseur/liste', views.situation_fournisseur,name="commerce_situationFournisseur"),
    path('commerce/fournisseur/recherche', views.recherche_fournisseur,name="commerce_rechercheFournisseur"),
    path('commerce/fournisseur/situation/etat', views.pdf_etat_situation_fournisseur,name="commerce_etatSituationFournisseur"),
    #-------------------Categories-------------------------
    path('categorie/', views.categorie_list_create,name="commerce_categorie"),    
    path('categorie/modification/<int:pk>/', views.categorie_edit,name="commerce_categorieEdit"),
    path('categorie/suppression/<int:pk>/', views.categorie_delete,name="commerce_categorieDelete"),
    #-------------------Produits-------------------------
    path('produit/', views.produit_list_create,name="commerce_produit"),    
    path('produit/modification/<int:pk>/', views.produit_edit,name="commerce_produitEdit"),
    path('produit/suppression/<int:pk>/', views.produit_delete,name="commerce_produitDelete"),
    path('get-produit-details/', views.get_produit_details, name='get_produit_details'),
    path('produitDisponible', views.produit_list,name="produitDisponible"),
    path('produit/recherche', views.recherche_produit,name="rechercheProduit"),
    path('produit/pdf/produitDisponible', views.pdf_Produit_disponible,name="pdfProduitDisponible"),
    path('produit/pdf/produitLivrer', views.pdf_Produit_livrer,name="pdfProduitLivrer"),
    path('produitLivrer', views.produit_livrer,name="produitLivrer"),
    path('produit/rechercheLivrer', views.recherche_produit_livrer,name="rechercheProduitLivrer"),
    path('produit/perime', views.produit_perime,name="commerce_produitPerime"),    
    path('produits/perime/etat', views.pdf_etat_produit_perime,name="commerce_etatProduitPerime"),
    path('produit/rupture', views.produit_rupture,name="commerce_produitEnRupture"),    
    path('produits/rupture/etat', views.pdf_etat_produit_rupture,name="commerce_etatProduitEnRupture"),
    #-------------------Reception-------------------------
    path('reception/', views.reception_create,name="commerce_reception"),    
    path('reception/detail/<int:pk>/', views.detail_reception,name="commerce_detailReception"),
    path('reception/modification/<int:pk>/', views.reception_edit,name="commerce_modReception"),
    path('reception/suppression/<int:pk>/', views.reception_delete,name="commerce_receptionDelete"),
    path('reception/supLivraisonProduit/<int:pk>/', views.produit_livrer_delete,name="commerce_deleteReception"),
    #-------------------Vente-------------------------
    path('vente/', views.vente_creates,name="commerce_vente"),    
    path('vente/modification/<int:pk>/', views.produit_edit,name="commerce_venteEdit"),
    path('vente/suppression/<int:pk>/', views.vente_delete,name="commerce_venteDelete"),
    path('vente/commande/modification/<int:pk>/', views.modifier_commande,name="commerce_modVente"),
    path('vente/commande/suppression/', views.commandeP_delete,name="commerce_commandePDelete"),
    path('vente/recu/<int:pk>/', views.recu,name="commerce_recu"),
    path("recu-offline/", views.recu_offline, name="recu_offline"),
    path('vente/produitVendu', views.produit_vendu, name="commerce_produitVendu"),
    path('vente/recherche/vente', views.recherche_vente,name="rechercheVente"),
    path('vente/produitParVente', views.produit_par_vente, name="produitParVente"),
    path('vente/situation', views.situation_vente,name="situationVente"),
    path('vente/recherche/situation', views.recherche_situation_vente,name="rechercheSituationVente"),
    path('vente/situation/etat', views.pdf_etat_situation_vente,name="pdfSituationVente"),
    path('vente/detail/vente', views.detail_vente,name="detailVente"),
    path('vente/recherche/detail/vente', views.recherche_detail_vente,name="rechercheDetailVente"),
    path('vente/client', views.vente_par_client, name="commerce_venteParClient"),
    path('vente/recherche/vente/client', views.recherche_vente_client,name="rechercheVenteClient"),
    path('vente/recherche/vente/payement', views.recherche_vente_payement,name="rechercheVentePayement"),
    path('vente/payement', views.vente_par_payement, name="commerce_venteParPayement"),
    path('vente/recherche/vente/type', views.recherche_vente_type,name="rechercheVenteType"),
    path('vente/type', views.vente_par_type, name="commerce_venteParType"),
    path('vente/facture/proforma', views.pdf_facture_proforma, name="pdf_facture_proforma"),
    path('pdf/facture/<int:commande_id>/', views.pdf_facture_proforma_2, name='pdf_facture_proforma_2'),

    #--
    path('commerce/depense', views.depense_list_create,name="commerce_depense"),
    path('commerce/depense/modification/<int:pk>/', views.depense_edit,name="commerce_modDepense"),
    path('commerce/depense/suppression/<int:pk>/', views.depense_delete,name="commerce_supDepense"),
    path('commerce/depense/liste', views.depense_list,name="commerce_listeDepense"),
    path('commerce/depense/recherche', views.recherche_depense,name="commerce_rechercheDepense"),
    path('commerce/depense/etat', views.pdf_etat_depense,name="commerce_etatDepense"),
    #--
    path('commerce/categories', views.categorie_depense_list_create,name="commerce_categorieDepense"),
    path('commerce/categorie/modification/<int:pk>/', views.categorie_depense_edit,name="commerce_modCategorieDepense"),
    path('commerce/categorie/suppression/<int:pk>/', views.categorie_depense_delete,name="commerce_supCategorieDepense"),
    #--
    path('commerce/versementClient', views.versementClient_list_create,name="commerce_versementClient"),
    path('commerce/versementClient/modification/<int:pk>/', views.versementClient_edit,name="commerce_modVersementClient"),
    path('commerce/versementClient/suppression/<int:pk>/', views.versementClient_delete,name="commerce_supVersementClient"),
    path('commerce/versementClient/liste', views.versementClient_list,name="commerce_listeVersementClient"),
    path('commerce/versementClient/recherche', views.recherche_versementClient,name="commerce_rechercheVersementClient"),
    path('commerce/versementClient/etat', views.pdf_etat_versementClient,name="commerce_etatVersementClient"),
    path('versement/recu/<int:versement_id>/', views.imprimer_recu_versement, name='imprimer_recu_versement'),
    path('client/situation/<int:client_id>/', views.imprimer_situation_client, name='imprimer_situation_client'),


    #-- client
    path('commerce/client', views.client_list_create,name="commerce_client"),
    path('commerce/client/modification/<int:pk>/', views.client_edit,name="commerce_modClient"),
    path('commerce/client/suppression/<int:pk>/', views.client_delete,name="commerce_supClient"),
    path('commerce/client/liste', views.client_list,name="commerce_listeClient"),
    path('commerce/client/recherche', views.recherche_client,name="commerce_rechercheClient"),
    path('commerce/client/etat', views.pdf_etat_client,name="commerce_etatClient"),
    path('commerce/client/situation/etat', views.pdf_etat_situation_client,name="commerce_etatListeClient"),
    #-- pretClient
    path('commerce/pret/Client', views.pretClient_list_create,name="commerce_pretClient"),
    path('commerce/pret/client/modification/<int:pk>/', views.pretClient_edit,name="commerce_modPretClient"),
    path('commerce/pret/client/suppression/<int:pk>/', views.pretClient_delete,name="commerce_supPretClient"),
    path('commerce/pret/client/liste', views.pretClient_list,name="commerce_listePretClient"),
    path('commerce/pret/client/recherche', views.recherche_pretClient,name="commerce_recherchePretClient"),
    path('commerce/pret/detail/<int:pk>/', views.detail_pret_client,name="commerce_detailClient"),
    path('commerce/pret/client/etat', views.pdf_etat_pretClient,name="commerce_etatPretClient"),
    path('commerce/client/reste/<int:id>/', views.get_reste_client, name='get_reste_client'),

    #-- fournisseur
    path('commerce/fournisseur', views.fournisseur_list_create,name="commerce_fournisseur"),
    path('commerce/fournisseur/modification/<int:pk>/', views.fournisseur_edit,name="commerce_modFournisseur"),
    path('commerce/fournisseur/suppression/<int:pk>/', views.fournisseur_delete,name="commerce_supFournisseur"),
    #-- versement fournisseur
    path('commerce/versementFournisseur', views.versementFournisseur_list_create,name="commerce_versementFournisseur"),
    path('commerce/versementFournisseur/modification/<int:pk>/', views.versementFournisseur_edit,name="commerce_modVersementFournisseur"),
    path('commerce/versementFournisseur/suppression/<int:pk>/', views.versementFournisseur_delete,name="commerce_supVersementFournisseur"),
    #path('commerce/versementFournisseur/liste', views.versementFournisseur_list,name="commerce_listeVersementFournisseur"),
    #path('commerce/versementFournisseur/recherche', views.recherche_versementFournisseur,name="commerce_rechercheVersementFournisseur"),
    #path('commerce/versementFournisseur/etat', views.pdf_etat_versementFournisseur,name="commerce_etatVersementFournisseur"),        
     #-- versement fournisseur
    path('commerce/detteFournisseur', views.detteFournisseur_list_create,name="commerce_detteFournisseur"),
    path('commerce/detteFournisseur/modification/<int:pk>/', views.detteFournisseur_edit,name="commerce_modDetteFournisseur"),
    path('commerce/detteFournisseur/suppression/<int:pk>/', views.detteFournisseur_delete,name="commerce_supDetteFournisseur"),
    #-- societe
    path('commerce/societe', views.societe_list_create,name="commerce_societe"),
    path('commerce/societe/modification/<int:pk>/', views.societe_edit,name="commerce_modSociete"),
    path('commerce/societe/suppression/<int:pk>/', views.societe_delete,name="commerce_supSociete"),
    #-- autres
    path('bilan', views.bilan,name="commerce_bilan"),
    path('bilan/recherche', views.recherche_bilan,name="rechercheBilan"),
    path('commerce/situation/boutique', views.situation_boutique,name="commerce_situationBoutique"),
    path('commerce/recherche/situation/boutique', views.recherche_situation_boutique,name="commerce_rechercheSituationBoutique"),
    path('commerce/situation/boutique/etat', views.pdf_etat_situation_boutique,name="commerce_etatSituationBoutique"),
    path('commerce/beneficevente', views.benefice_sur_vente,name="commerce_beneficeSurVente"),
    path('commerce/benefice/recherche', views.recherche_benefice_sur_vente,name="commerce_rechercheBeneficeSurVente"),
    #-- versement gerant
    path('commerce/versementGerant', views.versementGerant_list_create,name="commerce_versementGerant"),
    path('commerce/versementGerant/modification/<int:pk>/', views.versementGerant_edit,name="commerce_modVersementGerant"),
    path('commerce/versementGerant/suppression/<int:pk>/', views.versementGerant_delete,name="commerce_supVersementGerant"),
    path('commerce/versementGerant/liste', views.versementGerant_list,name="commerce_listeVersementGerant"),
    path('commerce/versementGerant/recherche', views.recherche_versementGerant,name="commerce_rechercheVersementGerant"),
    path('commerce/versementGerant/etat', views.pdf_etat_versementGerant,name="commerce_etatVersementGerant"),
    #-- inventaire
    path('commerce/inventaire', views.inventaire,name="inventaire"),
    path('commerce/inventaire/etat', views.pdf_inventaire,name="etatInventaire"),
    #-- Reception par produit
    path('commerce/reception/produit', views.reception_par_produit,name="receptionParProduit"),
    path('commerce/reception/produit/recheche', views.recherche_reception_produit, name="rechercheReceptionParProduit"),
    path('commerce/reception/produit/etat', views.pdf_etat_reception_produit, name="pdfReceptionParProduit"),
    #-- Caisse 
    path('commerce/caisse', views.caisse, name="caisse"),

    
    path('retours', views.retours, name='retours'),
    path('retours/ajouter/', views.enregistrer_retours, name='ajouter_retours'),
    path('retours/recherche', views.recherche_retours,name="rechercheRetours"),
    path('retours/delete/<int:pk>/', views.retour_delete,name="deleteRetours"),



    
    path('charge/donnee', views.import_excel_view,name="chargeDonnee"),



    # APIs offline
    #path("api/produits-min/", views.produits_min, name="api_produits_min"),
    path("api/sync/ventes/", views.sync_ventes, name="sync_ventes"),
    #path("api/sync/livraisons/", views.sync_livraisons, name="api_sync_livraisons"),
    path("api/produits/", views.api_produits, name="api_produits"),

    path("api/reception/", views.api_reception, name="api_reception"),
    path("api/sync/livraisons/", views.api_sync_livraisons, name="api_sync_livraisons"),


]