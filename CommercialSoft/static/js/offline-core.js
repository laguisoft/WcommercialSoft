// static/js/offline-core.js
//
// Synchronisation hors-ligne (ventes + réceptions) : chargé depuis
// starter-page.html en dehors de {% block js %}, donc exécuté sur TOUTE
// page affichée après connexion — pas seulement quand l'utilisateur ouvre
// la page de vente ou de réception concernée.

localforage.config({
  name: "venteApp", // même DB que vente2.html / reception2.html, pour partager les clés
});

function _csrfToken() {
  return window.CSRF_TOKEN || "";
}

let _syncVentesEnCours = false;

// Synchronise les ventes enregistrées localement (clé "ventes"), une par
// une, dans l'ordre — même format d'appel que /commerce/api/sync/ventes/
// attend (un objet vente par requête, pas un tableau).
async function syncVentesOffline() {
  if (_syncVentesEnCours) return;
  _syncVentesEnCours = true;
  try {
    const etat = document.getElementById("etatSynchro");
    let ventes = (await localforage.getItem("ventes")) || [];
    if (!ventes.length) {
      if (etat) {
        etat.innerHTML = "✅ Toutes les ventes sont synchronisées !";
        etat.style.color = "lime";
      }
      return;
    }

    for (let i = 0; i < ventes.length; i++) {
      try {
        const resp = await fetch("/commerce/api/sync/ventes/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(ventes[i]),
        });
        const out = await resp.json();
        if (out.success) {
          ventes.splice(i, 1);
          i--;
          await localforage.setItem("ventes", ventes);
        } else {
          console.warn("⚠️ Erreur sync vente:", out.error || out.message);
        }
      } catch (err) {
        console.error("❌ Erreur réseau, arrêt de la synchronisation des ventes.");
        break;
      }

      if (etat) {
        if (ventes.length > 0) {
          etat.innerHTML = `Reste ${ventes.length} ventes à synchroniser...`;
          etat.style.color = "orange";
        } else {
          etat.innerHTML = "✅ Toutes les ventes sont synchronisées !";
          etat.style.color = "lime";
        }
      }
      await new Promise((r) => setTimeout(r, 500));
    }

    if (!ventes.length) await localforage.removeItem("ventes");
  } finally {
    _syncVentesEnCours = false;
  }
}

let _syncLivraisonsEnCours = false;

// Synchronise les réceptions/livraisons enregistrées localement (clé
// "livraisons"), une par une — même principe que syncVentesOffline.
async function syncLivraisonsOffline() {
  if (_syncLivraisonsEnCours) return;
  _syncLivraisonsEnCours = true;
  try {
    const etat = document.getElementById("etatSynchroReception");
    let livraisons = (await localforage.getItem("livraisons")) || [];
    if (!livraisons.length) {
      if (etat) {
        etat.innerHTML = "✅ Toutes les factures sont synchronisées !";
        etat.style.color = "lime";
      }
      return;
    }

    for (let i = 0; i < livraisons.length; i++) {
      try {
        const resp = await fetch("/commerce/api/sync/livraisons/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(livraisons[i]),
        });
        const out = await resp.json();
        if (out.success) {
          livraisons.splice(i, 1);
          i--;
          await localforage.setItem("livraisons", livraisons);
        } else {
          console.warn("⚠️ Erreur sync livraison:", out.error);
        }
      } catch (err) {
        console.error("❌ Erreur réseau, arrêt de la synchronisation des livraisons.");
        break;
      }

      if (etat) {
        if (livraisons.length > 0) {
          etat.innerHTML = `Reste ${livraisons.length} facture(s) à synchroniser...`;
          etat.style.color = "orange";
        } else {
          etat.innerHTML = "✅ Toutes les factures sont synchronisées !";
          etat.style.color = "lime";
        }
      }
      await new Promise((r) => setTimeout(r, 400));
    }

    if (!livraisons.length) await localforage.removeItem("livraisons");
  } finally {
    _syncLivraisonsEnCours = false;
  }
}

function synchroniserToutHorsLigne() {
  syncVentesOffline();
  syncLivraisonsOffline();
}

// Synchro immédiate dès le chargement de la page (pas besoin d'attendre
// que l'utilisateur ouvre la page de vente ou de réception).
document.addEventListener("DOMContentLoaded", synchroniserToutHorsLigne);

// Rejoue dès que la connexion revient.
window.addEventListener("online", synchroniserToutHorsLigne);

// Quand le service worker envoie un message "PLEASE_SYNC".
navigator.serviceWorker?.addEventListener("message", (event) => {
  if (event.data?.type === "PLEASE_SYNC") synchroniserToutHorsLigne();
});

// Sondage régulier tant que l'app reste ouverte (données ajoutées
// hors-ligne entre deux tentatives).
setInterval(synchroniserToutHorsLigne, 10000);

window.offlineSync = { syncVentesOffline, syncLivraisonsOffline };
