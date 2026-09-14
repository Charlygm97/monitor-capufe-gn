// Service worker minimo: solo habilita que Android reconozca esto como
// una app instalable. Deja pasar todas las peticiones normalmente para
// que el dashboard siempre muestre los datos mas recientes (no se cachea
// nada, ya que necesitamos que eventos.json se lea siempre actualizado).

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
