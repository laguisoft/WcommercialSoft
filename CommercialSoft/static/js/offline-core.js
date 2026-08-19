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

// Retire un element synchronise avec succes d'une file relue a l'instant
// (pas d'un instantane pris en debut de boucle) : chaque envoi attend le
// reseau, donc si l'utilisateur ajoute une nouvelle vente/livraison pendant
// ce temps, une reecriture basee sur un instantane perime l'effacerait
// silencieusement avant meme qu'elle ait pu etre envoyee.
function _retirerDeFile(fileActuelle, elementEnvoye) {
  const idx = fileActuelle.findIndex((e) =>
    elementEnvoye.id_local
      ? e.id_local === elementEnvoye.id_local
      : JSON.stringify(e) === JSON.stringify(elementEnvoye)
  );
  if (idx === -1) return fileActuelle;
  const copie = fileActuelle.slice();
  copie.splice(idx, 1);
  return copie;
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
    const ventesAEnvoyer = (await localforage.getItem("ventes")) || [];
    if (!ventesAEnvoyer.length) {
      if (etat) {
        etat.innerHTML = "✅ Toutes les ventes sont synchronisées !";
        etat.style.color = "lime";
      }
      return;
    }

    for (const vente of ventesAEnvoyer) {
      let out;
      try {
        const resp = await fetch("/commerce/api/sync/ventes/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(vente),
        });
        out = await resp.json();
      } catch (err) {
        // Panne reseau, ou reponse non-JSON (ex: session expiree -> page de
        // login renvoyee a la place du JSON attendu) : on l'affiche au lieu
        // de laisser le compteur bloque sans explication, et on arrete pour
        // cette passe (on reessaiera au prochain sondage).
        const restantes = (await localforage.getItem("ventes")) || [];
        console.error("❌ Erreur réseau, arrêt de la synchronisation des ventes.", err);
        if (etat) {
          etat.innerHTML = `❌ Synchronisation interrompue (connexion ou session à reconnecter). Reste ${restantes.length} vente(s).`;
          etat.style.color = "red";
        }
        break;
      }

      if (out.success) {
        // Relit la file au lieu d'ecrire un instantane perime : une vente
        // ajoutee par l'utilisateur pendant cet envoi (attente reseau) ne
        // doit pas etre effacee par cette ecriture.
        const restantes = _retirerDeFile((await localforage.getItem("ventes")) || [], vente);
        await localforage.setItem("ventes", restantes);
        if (etat) {
          if (restantes.length > 0) {
            etat.innerHTML = `Reste ${restantes.length} ventes à synchroniser...`;
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

    const restantesFin = (await localforage.getItem("ventes")) || [];
    if (!restantesFin.length) await localforage.removeItem("ventes");
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
    const livraisonsAEnvoyer = (await localforage.getItem("livraisons")) || [];
    if (!livraisonsAEnvoyer.length) {
      if (etat) {
        etat.innerHTML = "✅ Toutes les factures sont synchronisées !";
        etat.style.color = "lime";
      }
      return;
    }

    for (const livraison of livraisonsAEnvoyer) {
      let out;
      try {
        const resp = await fetch("/commerce/api/sync/livraisons/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": _csrfToken() },
          credentials: "same-origin",
          body: JSON.stringify(livraison),
        });
        out = await resp.json();
      } catch (err) {
        const restantes = (await localforage.getItem("livraisons")) || [];
        console.error("❌ Erreur réseau, arrêt de la synchronisation des livraisons.", err);
        if (etat) {
          etat.innerHTML = `❌ Synchronisation interrompue (connexion ou session à reconnecter). Reste ${restantes.length} facture(s).`;
          etat.style.color = "red";
        }
        break;
      }

      if (out.success) {
        // Cf. syncVentesOffline : relit la file au lieu d'ecrire un
        // instantane perime, pour ne pas effacer une facture ajoutee
        // pendant cet envoi.
        const restantes = _retirerDeFile((await localforage.getItem("livraisons")) || [], livraison);
        await localforage.setItem("livraisons", restantes);
        if (etat) {
          if (restantes.length > 0) {
            etat.innerHTML = `Reste ${restantes.length} facture(s) à synchroniser...`;
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

    const restantesFin = (await localforage.getItem("livraisons")) || [];
    if (!restantesFin.length) await localforage.removeItem("livraisons");
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
