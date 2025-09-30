// static/js/offline-core.js

// ⚡ Initialisation localForage
localforage.config({
  name: "CommercialSoftOfflineDB",
  storeName: "ventes", // table pour les ventes hors-ligne
});

// Générer un UUID simple
function uuid() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Sauvegarder une vente hors-ligne
async function pushVenteOffline(vente) {
  vente._id = uuid(); // identifiant unique local
  await localforage.setItem(vente._id, vente);
  console.log("✅ Vente stockée hors-ligne:", vente);
}

// Synchroniser toutes les ventes
async function syncVentes() {
  const ventes = [];
  await localforage.iterate((value, key) => {
    ventes.push(value);
  });

  if (!ventes.length) {
    console.log("Aucune vente à synchroniser.");
    return;
  }

  console.log("🔄 Tentative de synchronisation des ventes:", ventes);

  try {
    const resp = await fetch("/commerce/api/sync/ventes/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ ventes }),
    });

    if (resp.ok) {
      console.log("✅ Synchronisation réussie !");
      // vider les ventes synchronisées
      await localforage.clear();
    } else {
      console.error("❌ Erreur API sync:", resp.status, await resp.text());
    }
  } catch (err) {
    console.error("⚠️ Impossible de synchroniser:", err);
  }
}

// Quand la connexion revient en ligne
window.addEventListener("online", () => {
  console.log("🌐 Connexion rétablie → sync");
  syncVentes();
});

// Quand le SW envoie un message "PLEASE_SYNC"
navigator.serviceWorker?.addEventListener("message", (event) => {
  if (event.data?.type === "PLEASE_SYNC") {
    syncVentes();
  }
});

// Exporter les fonctions
window.offlineCore = {
  uuid,
  pushVenteOffline,
  syncVentes,
};
