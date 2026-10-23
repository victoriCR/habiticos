// Activar o desactivar los recordatorios en ESTE teléfono (cada teléfono se activa aparte).

const seccion = document.getElementById("este-dispositivo");
const estado = document.getElementById("estado-dispositivo");
const botonActivar = document.getElementById("activar");
const botonDesactivar = document.getElementById("desactivar");
const token = document.querySelector("[name=csrfmiddlewaretoken]").value;

function mostrar(texto, { activar = false, desactivar = false } = {}) {
    estado.textContent = texto;
    botonActivar.hidden = !activar;
    botonDesactivar.hidden = !desactivar;
}

// La clave pública viene en base64 "para URLs"; el navegador la quiere en bytes
function claveEnBytes(base64) {
    const relleno = "=".repeat((4 - (base64.length % 4)) % 4);
    const texto = atob((base64 + relleno).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(texto, (letra) => letra.charCodeAt(0));
}

async function enviar(url, datos) {
    const respuesta = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token },
        body: JSON.stringify(datos),
    });
    if (!respuesta.ok || respuesta.redirected) throw new Error(respuesta.status);
}

async function revisar() {
    const esIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const instalada = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    if (esIOS && !instalada) {
        return mostrar("En el iPhone, primero instalá Habiticos: en Safari, tocá Compartir y después «Agregar a pantalla de inicio». Después abrila desde su ícono y volvé a esta página.");
    }
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
        return mostrar("Este navegador no permite notificaciones.");
    }
    if (document.body.dataset.pwa !== "activa") {
        return mostrar("Las notificaciones solo funcionan en habiticos.com (no en el modo de desarrollo).");
    }
    if (Notification.permission === "denied") {
        return mostrar("Bloqueaste las notificaciones de Habiticos. Para activarlas, cambiá el permiso en los ajustes del teléfono.");
    }
    const registro = await navigator.serviceWorker.ready;
    const suscripcion = await registro.pushManager.getSubscription();
    if (suscripcion) {
        mostrar("✅ Activados en este teléfono.", { desactivar: true });
    } else {
        mostrar("Desactivados en este teléfono.", { activar: true });
    }
}

botonActivar.addEventListener("click", async () => {
    try {
        // El permiso se pide solo después de tocar el botón (el iPhone lo exige)
        const permiso = await Notification.requestPermission();
        if (permiso !== "granted") return revisar();
        const registro = await navigator.serviceWorker.ready;
        const suscripcion = await registro.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: claveEnBytes(seccion.dataset.clave),
        });
        await enviar(seccion.dataset.suscribir, suscripcion.toJSON());
        location.reload();  // para que aparezca "Enviar una prueba"
    } catch (error) {
        mostrar("No se pudieron activar. Intentalo de nuevo.", { activar: true });
    }
});

botonDesactivar.addEventListener("click", async () => {
    try {
        const registro = await navigator.serviceWorker.ready;
        const suscripcion = await registro.pushManager.getSubscription();
        if (suscripcion) {
            await enviar(seccion.dataset.desuscribir, { endpoint: suscripcion.endpoint });
            await suscripcion.unsubscribe();
        }
        location.reload();
    } catch (error) {
        mostrar("No se pudieron desactivar. Intentalo de nuevo.", { desactivar: true });
    }
});

revisar();
