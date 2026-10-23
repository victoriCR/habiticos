// Habiticos como app instalable: registra el service worker y, si todavía no
// está instalada, muestra cómo instalarla (el iPhone no lo avisa solo).

const aviso = document.getElementById("instalar");

if (document.body.dataset.pwa === "activa" && "serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
}

function yaInstalada() {
    return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
}

function avisoCerrado() {
    try {
        return localStorage.getItem("habiticos-aviso-instalar") === "cerrado";
    } catch (error) {
        return false;  // sin almacenamiento (por ejemplo, navegación privada): se muestra
    }
}

function mostrarAviso(texto) {
    if (!aviso || yaInstalada() || avisoCerrado()) return;
    aviso.querySelector(".instalar-texto").textContent = texto;
    aviso.hidden = false;
}

// iPhone y iPad con Safari: hay que explicar los pasos
const esIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
const esSafari = !/crios|fxios|edgios/i.test(navigator.userAgent);
if (esIOS && esSafari) {
    mostrarAviso("Instalá Habiticos: tocá Compartir y después «Agregar a pantalla de inicio».");
}

// Android y Chrome: el navegador ofrece un botón propio
let pedidoDeInstalacion = null;
window.addEventListener("beforeinstallprompt", (evento) => {
    evento.preventDefault();
    pedidoDeInstalacion = evento;
    if (!aviso) return;
    aviso.querySelector(".instalar-boton").hidden = false;
    mostrarAviso("Instalá Habiticos en tu teléfono para abrirla como una app.");
});

if (aviso) {
    aviso.querySelector(".instalar-boton").addEventListener("click", async () => {
        if (!pedidoDeInstalacion) return;
        pedidoDeInstalacion.prompt();
        await pedidoDeInstalacion.userChoice;
        pedidoDeInstalacion = null;
        aviso.hidden = true;
    });
    aviso.querySelector(".instalar-cerrar").addEventListener("click", () => {
        aviso.hidden = true;
        try {
            localStorage.setItem("habiticos-aviso-instalar", "cerrado");
        } catch (error) {
            // sin almacenamiento: se cierra solo por esta vez
        }
    });
}
