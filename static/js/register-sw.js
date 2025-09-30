// static/js/register-sw.js

(async function registerSW() {
  if ("serviceWorker" in navigator) {
    try {
      const reg = await navigator.serviceWorker.register("/serviceworker.js");
      console.log("SW registered", reg);

      // Essaye d'enregistrer un background sync
      if ("sync" in reg) {
        try { await reg.sync.register("sync-all"); } catch (e) {}
      }

      // Quand le SW te dit "PLEASE_SYNC", lance la sync
      navigator.serviceWorker.addEventListener("message", (event) => {
        if (event.data && event.data.type === "PLEASE_SYNC") {
          if (window.offlineCore && typeof window.offlineCore.syncQueues === "function") {
            window.offlineCore.syncQueues();
          }
        }
      });
    } catch (e) {
      console.warn("SW registration failed", e);
    }
  }

  // Fallback: si on revient en ligne, tente la sync
  window.addEventListener("online", () => {
    if (window.offlineCore && typeof window.offlineCore.syncQueues === "function") {
      window.offlineCore.syncQueues();
    }
  });
})();
