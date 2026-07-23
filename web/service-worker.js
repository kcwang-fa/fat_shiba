const CACHE_PREFIX = "fat-shiba-pwa-";
const CACHE_NAME = `${CACHE_PREFIX}v20`;
const DATA_PATHS = [
  "/data/word-level-n5.js",
  "/data/word-level-n4.js",
  "/data/word-level-n3.js",
  "/data/word-level-n2.js",
  "/data/word-level-n1.js",
  "/data/word-meta-n5.js",
  "/data/word-meta-n4.js",
  "/data/word-meta-n3.js",
  "/data/word-meta-n2.js",
  "/data/word-meta-n1.js"
];
const REQUIRED_APP_SHELL = [
  "./",
  "./index.html",
  "./data/word-level-n5.js?v=20260720-n1-cleanup",
  "./assets/app-icon-180.png",
  "./assets/app-icon-192.png",
  "./assets/app-icon-512.png"
];
const OPTIONAL_APP_SHELL = [
  "./assets/home-journey.webp",
  "./assets/jlpt-map-entrance.webp",
  "./assets/jlpt-map-entrance-mobile.webp",
  "./assets/jlpt-map-entrance-mobile.png"
];

function isDataRequest(url) {
  return DATA_PATHS.some((path) => url.pathname.endsWith(path));
}

function isCacheableResponse(response) {
  return response && response.status === 200 && response.type === "basic";
}

async function fetchAndUpdateCache(request, cacheKey = request) {
  const response = await fetch(request);
  if (isCacheableResponse(response)) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(cacheKey, response.clone());
  }
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(async (cache) => {
        await cache.addAll(REQUIRED_APP_SHELL);

        const optionalResults = await Promise.allSettled(
          OPTIONAL_APP_SHELL.map((url) => cache.add(url))
        );
        for (const result of optionalResults) {
          if (result.status === "rejected") {
            console.warn("Optional app shell cache failed.", result.reason);
          }
        }
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
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
    const networkResponse = fetchAndUpdateCache(request, "./index.html");
    event.waitUntil(networkResponse.catch(() => {}));
    event.respondWith(
      caches.match("./index.html").then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return networkResponse.catch(() => caches.match("./index.html"));
      })
    );
    return;
  }

  if (isDataRequest(url)) {
    const networkResponse = fetchAndUpdateCache(request);
    event.waitUntil(networkResponse.catch(() => {}));
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
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

      return fetchAndUpdateCache(request);
    })
  );
});
