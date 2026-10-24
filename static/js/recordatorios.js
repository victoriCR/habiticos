// Activar o desactivar los recordatorios en ESTE dispositivo (cada uno se activa aparte).

const seccion = document.getElementById("este-dispositivo");
const estado = document.getElementById("estado-dispositivo");
const botonActivar = document.getElementById("activar");
const botonDesactivar = document.getElementById("desactivar");
const token = document.querySelector("[name=csrfmiddlewaretoken]").value;
const instalada = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

// ¿Celular, computadora o (si no se puede saber, o es una tablet) dispositivo?
// El navegador no dice el modelo, y el iPad se presenta como "Mac": por eso, ante la duda, "dispositivo"
function tipoDeDispositivo() {
    const ua = navigator.userAgent;
    const tactil = navigator.maxTouchPoints > 1;
    if (/iphone|ipod/i.test(ua) || /android.+mobile/i.test(ua) || navigator.userAgentData?.mobile) return "celular";
    if (/ipad|android|tablet/i.test(ua) || (/macintosh/i.test(ua) && tactil)) return "dispositivo";
    if (/macintosh|windows|cros|linux/i.test(ua)) return "computadora";
    return "dispositivo";
}

// Para la lista "Dónde están activos": "iPhone · app", "Mac · Chrome"
function nombreDelDispositivo() {
    const ua = navigator.userAgent;
    const tactil = navigator.maxTouchPoints > 1;
    const sistema =
        /iphone|ipod/i.test(ua) ? "iPhone"
        : /ipad/i.test(ua) || (/macintosh/i.test(ua) && tactil) ? "iPad"
        : /android/i.test(ua) ? "Android"
        : /macintosh/i.test(ua) ? "Mac"
        : /windows/i.test(ua) ? "Windows"
        : /cros/i.test(ua) ? "Chromebook"
        : /linux/i.test(ua) ? "Linux"
        : "";
    const navegador =
        instalada ? "app"
        : /edg\//i.test(ua) ? "Edge"
        : /firefox|fxios/i.test(ua) ? "Firefox"
        : /chrome|crios/i.test(ua) ? "Chrome"
        : /safari/i.test(ua) ? "Safari"
        : "";
    return [sistema, navegador].filter(Boolean).join(" · ");
}

const tipo = tipoDeDispositivo();
const este = { celular: "este celular", computadora: "esta computadora", dispositivo: "este dispositivo" }[tipo];
document.getElementById("titulo-dispositivo").textContent = `En ${este}`;
botonDesactivar.textContent = `Desactivar en ${este}`;

// Marca "· este" en la lista (comparando un resumen del endpoint, como hace el servidor)
async function marcarEste(endpoint) {
    if (!crypto.subtle) return;
    const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(endpoint));
    const huella = [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
    const fila = document.querySelector(`.dispositivos li[data-huella="${huella}"]`);
    if (fila) {
        fila.querySelector(".este").hidden = false;
        fila.querySelector("form").hidden = true;  // este se apaga con "Desactivar", arriba
    }
}

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

function datosDeSuscripcion(suscripcion, extra = {}) {
    return { ...suscripcion.toJSON(), tipo, nombre: nombreDelDispositivo(), ...extra };
}

async function revisar() {
    const esIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
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
        const donde = tipo === "celular" ? "los ajustes del celular" : "los ajustes del navegador";
        return mostrar(`Bloqueaste las notificaciones de Habiticos. Para activarlas, cambiá el permiso en ${donde}.`);
    }
    const registro = await navigator.serviceWorker.ready;
    const suscripcion = await registro.pushManager.getSubscription();
    if (suscripcion) {
        try {
            // Completa "celular"/"computadora" en las suscripciones anteriores a esto
            await enviar(seccion.dataset.suscribir, datosDeSuscripcion(suscripcion, { solo_actualizar: true }));
        } catch (error) {
            if (error.message === "404") {
                // Lo quitaron desde otro dispositivo: queda apagado también acá
                await suscripcion.unsubscribe();
                return mostrar(`Desactivados en ${este}.`, { activar: true });
            }
        }
        mostrar(`✅ Activados en ${este}.`, { desactivar: true });
        marcarEste(suscripcion.endpoint);
    } else {
        mostrar(`Desactivados en ${este}.`, { activar: true });
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
        await enviar(seccion.dataset.suscribir, datosDeSuscripcion(suscripcion));
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
