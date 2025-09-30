// static/js/offline-core.js

// ---- localForage ----
alert("offline-core.js loaded");
const scriptLF = document.createElement("script");
scriptLF.src = "https://cdn.jsdelivr.net/npm/localforage@1.10.0/dist/localforage.min.js";
document.head.appendChild(scriptLF);

window.offlineCore = (() => {
  const state = {
    produitsKey: "produits-cache-v1",
    ventesKey: "ventes:queue",
    livraisonsKey: "livraisons:queue",
    apiProduits: "/api/produits-min/",
    apiSyncVentes: "/api/sync/ventes/",
    apiSyncLivraisons: "/api/sync/livraisons/",
  };

  function uuid() {
    if (crypto?.randomUUID) return crypto.randomUUID();
    return "uid-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  async function readyLF() {
    await new Promise((res) => {
      if (window.localforage) return res();
      scriptLF.addEventListener("load", res);
    });
    localforage.config({ name: "commerce-offline" });
  }

  // ---- Produits ----
  async function refreshProduits() {
    await readyLF();
    const resp = await fetch(state.apiProduits, { credentials: "same-origin" });
    if (!resp.ok) throw new Error("Produits API error");
    const data = await resp.json();
    await localforage.setItem(state.produitsKey, data.produits || []);
    return data.produits || [];
  }

  async function getProduitsCached() {
    await readyLF();
    const cached = await localforage.getItem(state.produitsKey);
    return cached || [];
  }

  // ---- Queues ----
  async function pushVenteOffline(vente) {
    await readyLF();
    const q = (await localforage.getItem(state.ventesKey)) || [];
    q.push(vente);
    await localforage.setItem(state.ventesKey, q);
  }

  async function pushLivraisonOffline(liv) {
    await readyLF();
    const q = (await localforage.getItem(state.livraisonsKey)) || [];
    q.push(liv);
    await localforage.setItem(state.livraisonsKey, q);
  }

  async function popAllQueues() {
    await readyLF();
    const ventes = (await localforage.getItem(state.ventesKey)) || [];
    const livs = (await localforage.getItem(state.livraisonsKey)) || [];
    await localforage.setItem(state.ventesKey, []);
    await localforage.setItem(state.livraisonsKey, []);
    return { ventes, livs };
  }

  // ---- Sync ----
  async function postJSON(url, body) {
    const csrftoken = getCookie("csrftoken");
    const resp = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(csrftoken ? { "X-CSRFToken": csrftoken } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error("Sync error " + resp.status);
    return resp.json();
  }

  async function syncQueues() {
    if (!navigator.onLine) return;

    const { ventes, livs } = await popAllQueues();

    // Sync ventes
    if (ventes.length) {
      try {
        await postJSON(state.apiSyncVentes, { ventes });
      } catch (e) {
        // Echec: on remet en queue
        const old = (await localforage.getItem(state.ventesKey)) || [];
        await localforage.setItem(state.ventesKey, [...ventes, ...old]);
      }
    }

    // Sync livraisons
    if (livs.length) {
      try {
        await postJSON(state.apiSyncLivraisons, { livraisons: livs });
      } catch (e) {
        const old = (await localforage.getItem(state.livraisonsKey)) || [];
        await localforage.setItem(state.livraisonsKey, [...livs, ...old]);
      }
    }

    // Après sync réussie, on peut rafraîchir produits (stocks)
    try { await refreshProduits(); } catch (e) {}
  }

  return {
    uuid,
    refreshProduits,
    getProduitsCached,
    pushVenteOffline,
    pushLivraisonOffline,
    syncQueues,
  };
})();
