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

// Manejo de notificaciones push: cuando llega una notificacion del
// servidor de push (disparada por el monitor), se muestra en el celular.
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data.json();
  } catch (e) {
    data = { title: "Evento carretero", body: event.data ? event.data.text() : "" };
  }

  const titulo = data.title || "Evento carretero";
  const opciones = {
    body: data.body || "",
    icon: "icons/icon-192.png",
    badge: "icons/icon-192.png",
    data: { url: data.url || "." },
  };

  event.waitUntil(self.registration.showNotification(titulo, opciones));
});

// Al tocar la notificacion, abre (o enfoca) la app en la publicacion
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || "."));
});
