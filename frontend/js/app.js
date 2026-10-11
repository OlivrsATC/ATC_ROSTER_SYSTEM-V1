const API_URL = "http://127.0.0.1:8000/api";

document.addEventListener("DOMContentLoaded", () => {
    cargarControladores();

    // Manejar envío del formulario de nuevo controlador
    const formControlador = document.getElementById("formControlador");
    formControlador.addEventListener("submit", async (e) => {
        e.preventDefault();

        const data = {
            identificacion: document.getElementById("identificacion").value,
            nombres: document.getElementById("nombres").value,
            apellidos: document.getElementById("apellidos").value,
            email: document.getElementById("email").value,
            aptitud_psicofisica_vencimiento: document.getElementById("aptitud_psicofisica_vencimiento").value,
            rol: "CONTROLADOR",
            activo: true,
            autonomias: []
        };

        try {
            const response = await fetch(`${API_URL}/controladores/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const err = await response.json();
                alert(`Error: ${err.detail}`);
                return;
            }

            alert("Controlador registrado exitosamente.");
            formControlador.reset();
            bootstrap.Modal.getInstance(document.getElementById("modalControlador")).hide();
            cargarControladores();
        } catch (error) {
            console.error("Error de conexión:", error);
            alert("No se pudo conectar con el servidor backend.");
        }
    });
});

async function cargarControladores() {
    try {
        const response = await fetch(`${API_URL}/controladores/`);
        const controladores = await response.json();
        
        const tbody = document.querySelector("#tablaControladores tbody");
        tbody.innerHTML = "";

        if (controladores.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No hay controladores registrados.</td></tr>`;
            return;
        }

        controladores.forEach(c => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${c.identificacion}</td>
                <td>${c.nombres} ${c.apellidos}</td>
                <td>${c.email}</td>
                <td><span class="badge bg-secondary">${c.rol}</span></td>
                <td>${c.aptitud_psicofisica_vencimiento}</td>
                <td><span class="badge ${c.activo ? 'bg-success' : 'bg-danger'}">${c.activo ? 'Activo' : 'Inactivo'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="eliminarControlador('${c.id}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error cargando controladores:", error);
    }
}

async function eliminarControlador(id) {
    if (!confirm("¿Está seguro de eliminar este controlador?")) return;

    try {
        const response = await fetch(`${API_URL}/controladores/${id}`, {
            method: "DELETE"
        });

        if (response.ok) {
            alert("Controlador eliminado.");
            cargarControladores();
        } else {
            alert("Error al eliminar el controlador.");
        }
    } catch (error) {
        console.error("Error:", error);
    }
}