// Celular: el panel "Más" que sube desde abajo (un <dialog>: el navegador se
// encarga de oscurecer el fondo, cerrar con Esc y mantener el foco adentro).

const hoja = document.getElementById("mas");
const botonMas = document.getElementById("abrir-mas");

if (hoja && botonMas) {
    botonMas.addEventListener("click", () => {
        hoja.showModal();
        hoja.focus();  // el foco, en el panel (no en su primer enlace, que se vería marcado)
    });

    // Tocar la parte oscura (fuera del panel) lo cierra
    hoja.addEventListener("click", (evento) => {
        if (evento.target === hoja) hoja.close();
    });

    // Deslizar hacia abajo desde la parte de arriba del panel lo cierra
    let inicioY = null;
    hoja.addEventListener("touchstart", (evento) => {
        inicioY = hoja.scrollTop === 0 ? evento.touches[0].clientY : null;
    }, { passive: true });
    hoja.addEventListener("touchend", (evento) => {
        if (inicioY !== null && evento.changedTouches[0].clientY - inicioY > 60) hoja.close();
        inicioY = null;
    });
}
