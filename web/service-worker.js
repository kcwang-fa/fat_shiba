const CACHE_NAME = "fat-shiba-pwa-v9";
const DATA_PATHS = [
  "/data/word-level-n5.js",
  "/data/word-level-n4.js",
  "/data/word-level-n3.js",
  "/data/word-level-n2.js",
  "/data/word-level-n1.js",
  "/data/word_meta.js",
  "/data/word-meta-n5.js",
  "/data/word-meta-n4.js",
  "/data/word-meta-n3.js",
  "/data/word-meta-n2.js",
  "/data/word-meta-n1.js"
];
const APP_SHELL = [
  "./",
  "./index.html",
  "./data/word-level-n5.js?v=20260717-levels",
  "./assets/app-icon-180.png",
  "./assets/app-icon-192.png",
  "./assets/app-icon-512.png",
  "./assets/home-journey.webp",
  "./assets/jlpt-map-entrance.webp",
  "./assets/jlpt-map-entrance-mobile.webp",
  "./assets/jlpt-map-entrance-mobile.png"
];

function isDataRequest(url) {
  return DATA_PATHS.some((path) => url.pathname.endsWith(path));
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => Promise.allSettled(APP_SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      caches.match("./index.html").then((cachedResponse) => {
        const networkResponse = fetch(request).then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            caches.open(CACHE_NAME).then((cache) => cache.put("./index.html", response.clone()));
          }
          return response;
        });
        if (cachedResponse) {
          networkResponse.catch(() => {});
          return cachedResponse;
        }
        return networkResponse.catch(() => caches.match("./index.html"));
      })
    );
    return;
  }

  if (isDataRequest(url)) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const networkResponse = fetch(request).then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
          }
          return response;
        });
        if (cachedResponse) {
          networkResponse.catch(() => {});
          return cachedResponse;
        }
        return networkResponse.catch(() => caches.match(request));
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) return cachedResponse;

      return fetch(request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== "basic") {
          return networkResponse;
        }

        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, responseToCache);
        });
        return networkResponse;
      });
    })
  );
});
