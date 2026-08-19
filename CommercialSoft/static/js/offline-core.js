// static/js/offline-core.js
//
// Synchronisation hors-ligne (ventes + réceptions). Chargé uniquement par
// vente2.html (page de vente) et reception2.html (page de réception) — plus
// depuis starter-page.html — pour que la synchro ne tourne que dans la
// fenêtre concernée, pas sur tout l'app. synchroniserToutHorsLigne() ne
// déclenche donc que la partie utile à la page ouverte (cf. plus bas, via
// la présence de #etatSynchro / #etatSynchroReception).

// localforage est chargé en auto-hébergé (voir starter-page.html / vente2.html) pour
// rester disponible hors-ligne, mais si le script n'a pas pu se charger (cache PWA pas
// encore rempli, fichier statique manquant...) on évite qu'une ReferenceError ici ne
// tue le reste de ce script : sans ce garde, aucun des listeners plus bas (sync auto au
// chargement, à la reconnexion, au message du service worker) ne serait jamais enregistré.
if (typeof localforage === "undefined") {
  console.error("❌ localforage indisponible : synchronisation hors-ligne désactivée pour cette page.");
} else {
  localforage.config({
    name: "venteApp", // même DB que vente2.html / reception2.html, pour partager les clés
  });
}

function _csrfToken() {
  return window.CSRF_TOKEN || "";
}

let _syncVentesEnCours = false;

// Synchronise les ventes enregistrées localement (clé "ventes"), une par
// une, dans l'ordre — même format d'appel que /commerce/api/sync/ventes/
// attend (un objet vente par requête, pas un tableau).
async function syncVentesOffline() {
  if (typeof localforage === "undefined" || _syncVentesEnCours) return;
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
      let out;
      try {
        const resp = await fetch("/commerce/api/sync/ventes/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(ventes[i]),
        });
        out = await resp.json();
      } catch (err) {
        // Panne reseau, ou reponse non-JSON (ex: session expiree -> page de
        // login renvoyee a la place du JSON attendu) : on l'affiche au lieu
        // de laisser le compteur bloque sans explication, et on arrete pour
        // cette passe (on reessaiera au prochain sondage).
        console.error("❌ Erreur réseau, arrêt de la synchronisation des ventes.", err);
        if (etat) {
          etat.innerHTML = `❌ Synchronisation interrompue (connexion ou session à reconnecter). Reste ${ventes.length} vente(s).`;
          etat.style.color = "red";
        }
        break;
      }

      if (out.success) {
        ventes.splice(i, 1);
        i--;
        await localforage.setItem("ventes", ventes);
        if (etat) {
          if (ventes.length > 0) {
            etat.innerHTML = `Reste ${ventes.length} ventes à synchroniser...`;
            etat.style.color = "orange";
          } else {
            etat.innerHTML = "✅ Toutes les ventes sont synchronisées !";
            etat.style.color = "lime";
          }
        }
      } else {
        // Vente rejetee par le serveur (donnees invalides, produit
        // supprime depuis...) : on l'affiche pour que ce ne soit pas juste
        // "bloque" sans explication a l'ecran, et on passe a la suivante
        // plutot que de reessayer en boucle la meme vente indefiniment.
        console.warn("⚠️ Erreur sync vente:", out.error || out.message);
        if (etat) {
          etat.innerHTML = `⚠️ Vente non synchronisée : ${out.message || out.error || "erreur inconnue"}`;
          etat.style.color = "red";
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
  if (typeof localforage === "undefined" || _syncLivraisonsEnCours) return;
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
      let out;
      try {
        const resp = await fetch("/commerce/api/sync/livraisons/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(livraisons[i]),
        });
        out = await resp.json();
      } catch (err) {
        console.error("❌ Erreur réseau, arrêt de la synchronisation des livraisons.", err);
        if (etat) {
          etat.innerHTML = `❌ Synchronisation interrompue (connexion ou session à reconnecter). Reste ${livraisons.length} facture(s).`;
          etat.style.color = "red";
        }
        break;
      }

      if (out.success) {
        livraisons.splice(i, 1);
        i--;
        await localforage.setItem("livraisons", livraisons);
        if (etat) {
          if (livraisons.length > 0) {
            etat.innerHTML = `Reste ${livraisons.length} facture(s) à synchroniser...`;
            etat.style.color = "orange";
          } else {
            etat.innerHTML = "✅ Toutes les factures sont synchronisées !";
            etat.style.color = "lime";
          }
        }
      } else {
        console.warn("⚠️ Erreur sync livraison:", out.error);
        if (etat) {
          etat.innerHTML = `⚠️ Facture non synchronisée : ${out.error || out.message || "erreur inconnue"}`;
          etat.style.color = "red";
        }
      }
      await new Promise((r) => setTimeout(r, 400));
    }

    if (!livraisons.length) await localforage.removeItem("livraisons");
  } finally {
    _syncLivraisonsEnCours = false;
  }
}

// Ne lance que la synchro utile à la page actuellement ouverte : #etatSynchro
// n'existe que sur la page de vente, #etatSynchroReception que sur celle de
// réception — c'est ce qui limite la synchro à la fenêtre concernée.
function synchroniserToutHorsLigne() {
  if (document.getElementById("etatSynchro")) syncVentesOffline();
  if (document.getElementById("etatSynchroReception")) syncLivraisonsOffline();
}

// Synchro immédiate dès le chargement de la page de vente ou de réception.
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
