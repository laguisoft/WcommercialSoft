// CommercialSoft/templates/CommercialSoft/serviceworker.js

const CACHE_NAME = "app-shell-v1";
const APP_SHELL = [
  "/",                 
  "/offline/",           // on ajoute la page offline
  "/static/js/register-sw.js",
  "/static/js/offline-core.js",
  "/static/js/vente.js",
  "/commerce/vente/",          // page de vente
  "/commerce/dashboard/",
  // ajoute aussi tes images/icônes ex :
  // "/static/images/icons/icon-192x192.png",
];

// INSTALL
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// ACTIVATE
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k))))
    )
  );
  self.clients.claim();
});

// FETCH
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  // Cache-first pour les assets statiques
  if (event.request.url.includes("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // Network-first avec fallback cache et offline page
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request) || caches.match("/offline/"))
  );
});

// BACKGROUND SYNC
self.addEventListener("sync", (event) => {
  if (["sync-ventes", "sync-livraisons", "sync-all"].includes(event.tag)) {
    event.waitUntil(
      self.clients.matchAll({ includeUncontrolled: true, type: "window" })
        .then((clients) => {
          clients.forEach((c) => c.postMessage({ type: "PLEASE_SYNC" }));
        })
    );
  }
});
