// Ordenar arrastrando el asa ⠿ (usa SortableJS).
//
// Uso en una plantilla:
//   <div data-ordenar="/url/que/guarda/">
//     <ul class="ordenable">
//       <li class="fila" data-id="3"><span class="asa">⠿</span> …</li>
//     </ul>
//   </div>
//
// Puede haber varias listas .ordenable (por ejemplo, un grupo por identidad):
// cada fila se mueve solo dentro de su lista, y al soltar se envían los ids
// de todas, en el orden en que aparecen en la página.

function hacerOrdenable(contenedor) {
    const url = contenedor.dataset.ordenar;

    contenedor.querySelectorAll(".ordenable").forEach((lista) => {
        Sortable.create(lista, {
            handle: ".asa",
            draggable: ".fila",
            animation: 150,
            ghostClass: "arrastrando",
            onEnd: guardarOrden,
        });
    });

    async function guardarOrden() {
        const ids = [...contenedor.querySelectorAll(".ordenable .fila")].map((fila) => fila.dataset.id);
        const token = document.querySelector("[name=csrfmiddlewaretoken]").value;
        try {
            const respuesta = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": token },
                body: JSON.stringify({ orden: ids }),
            });
            // redirected: la sesión caducó (medianoche) y nos mandaron al login
            if (!respuesta.ok || respuesta.redirected) throw new Error(respuesta.status);
        } catch (error) {
            // Si no se pudo guardar, recargamos para mostrar el orden real
            alert("No se pudo guardar el nuevo orden. Intentalo de nuevo.");
            location.reload();
        }
    }
}

document.querySelectorAll("[data-ordenar]").forEach(hacerOrdenable);
