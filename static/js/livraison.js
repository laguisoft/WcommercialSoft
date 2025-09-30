// static/js/livraison.js

(async function initLivraison() {
  const select = document.querySelector("#livraison-produit-select");
  const qteInput = document.querySelector("#livraison-quantite");
  const prixInput = document.querySelector("#livraison-prix-achat");
  const prixDetailInput = document.querySelector("#livraison-prix-detail");
  const fournisseurSelect = document.querySelector("#livraison-fournisseur-select");
  const factureInput = document.querySelector("#livraison-facture");
  const peremptionInput = document.querySelector("#livraison-peremption");
  const btn = document.querySelector("#btn-livrer");

  async function fillProduits() {
    let produits = [];
    try {
      produits = await offlineCore.refreshProduits();
    } catch (e) {
      produits = await offlineCore.getProduitsCached();
    }
    if (select) {
      select.innerHTML = '<option value="">-- Sélectionner --</option>';
      produits.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.libelle} (Stock: ${p.quantite})`;
        select.appendChild(opt);
      });
    }
  }

  await fillProduits();

  async function handleLivrer() {
    const produit_id = parseInt(select.value);
    const quantite = parseInt(qteInput.value || "0");
    const prix = parseInt(prixInput.value || "0");
    const prixDetail = parseInt(prixDetailInput.value || "0");
    const fournisseur_id = fournisseurSelect?.value ? parseInt(fournisseurSelect.value) : null;
    const numeroFacture = factureInput?.value || null;
    const peremption = peremptionInput?.value || new Date().toISOString().slice(0, 10);
    const date = new Date().toISOString().slice(0, 10);

    if (!produit_id || !quantite || !prix || !fournisseur_id) {
      alert("Produit/Quantité/Prix/Fournisseur manquant.");
      return;
    }

    const lv = {
      client_uid: offlineCore.uuid(),
      fournisseur_id,
      numeroFacture,
      date,
      items: [{ produit_id, quantite, prix, prixDetail, peremption }],
    };

    if (navigator.onLine) {
      try {
        await fetch("/api/sync/livraisons/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ livraisons: [lv] }),
        });
        alert("Réception enregistrée (en ligne).");
        await offlineCore.refreshProduits();
        await fillProduits();
        return;
      } catch (e) {}
    }

    await offlineCore.pushLivraisonOffline(lv);
    alert("Hors-ligne: réception enregistrée localement. Elle sera synchronisée.");
  }

  btn?.addEventListener("click", handleLivrer);
})();
