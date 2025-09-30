// static/js/register-sw.js

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/serviceworker.js")
      .then((reg) => {
        console.log("Service Worker enregistré ✅", reg.scope);
      })
      .catch((err) => {
        console.error("Erreur enregistrement Service Worker ❌", err);
      });
  });
}
