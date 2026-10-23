// Service worker de Habiticos: lo instala el navegador junto con la app.
// Solo guarda el diseño (CSS, JS, íconos) y la pantalla "Sin conexión":
// las páginas con tus datos siempre se piden al servidor, para no mostrar rachas viejas.

const CACHE = "habiticos-{{ version }}";
const SIN_CONEXION = "{% url 'sin_conexion' %}";
const PRECARGA = [SIN_CONEXION{% for archivo in precarga %}, "{{ archivo }}"{% endfor %}];
const ESTATICOS = "{{ prefijo_estaticos }}";

self.addEventListener("install", (evento) => {
    evento.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECARGA)));
    self.skipWaiting();  // la versión nueva empieza a funcionar enseguida
});

self.addEventListener("activate", (evento) => {
    // Borrar lo guardado por versiones anteriores
    evento.waitUntil(
        caches.keys()
            .then((nombres) => Promise.all(nombres.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (evento) => {
    const pedido = evento.request;
    const url = new URL(pedido.url);
    if (pedido.method !== "GET" || url.origin !== location.origin) return;

    // Páginas: siempre del servidor; si no hay internet, "Sin conexión"
    if (pedido.mode === "navigate") {
        evento.respondWith(fetch(pedido).catch(() => caches.match(SIN_CONEXION)));
        return;
    }

    // Diseño: primero lo guardado (los nombres cambian con cada versión, nunca queda viejo)
    if (url.pathname.startsWith(ESTATICOS)) {
        evento.respondWith(
            caches.match(pedido).then((guardado) => guardado || fetch(pedido).then((respuesta) => {
                if (respuesta.ok) {
                    const copia = respuesta.clone();
                    caches.open(CACHE).then((cache) => cache.put(pedido, copia));
                }
                return respuesta;
            }))
        );
    }
});
