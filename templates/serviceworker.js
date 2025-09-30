// templates/serviceworker.js

const CACHE_NAME = "app-shell-v1";
const APP_SHELL = [
  "/",                 // ta page d'accueil
  "/static/css/base.css",
  "/static/js/register-sw.js",
  "/static/js/offline-core.js",
  "/static/js/vente.js",
  "/static/js/livraison.js",
  // ajoute tes images/icônes…
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k))))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Cache-first pour les assets statiques
  if (request.method === "GET" && request.url.includes("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }
  // Network-first avec fallback cache (utile pour HTML)
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

// Background Sync: réveille la page pour lancer la sync côté client
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-ventes" || event.tag === "sync-livraisons" || event.tag === "sync-all") {
    event.waitUntil(
      self.clients.matchAll({ includeUncontrolled: true, type: "window" })
        .then((clients) => {
          clients.forEach((c) => c.postMessage({ type: "PLEASE_SYNC" }));
        })
    );
  }
});
