const API_URL = "http://127.0.0.1:8000/api";
let listaControladoresCache = [];

document.addEventListener("DOMContentLoaded", () => {
    cargarControladores();
    cargarTurnosAsignados();

    // Formulario Registro Controlador
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

    // Formulario Asignación de Turno
    const formTurno = document.getElementById("formTurno");
    formTurno.addEventListener("submit", async (e) => {
        e.preventDefault();

        const data = {
            controlador_id: document.getElementById("selectControlador").value,
            turno_codigo: document.getElementById("selectTurnoCodigo").value,
            fecha: document.getElementById("fechaTurno").value
        };

        try {
            const response = await fetch(`${API_URL}/turnos/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const err = await response.json();
                alert(`⚠️ RESTRICCIÓN OPERATIVA (Motor de Reglas):\n\n${err.detail}`);
                return;
            }

            alert("¡Turno asignado exitosamente validando normas de fatiga!");
            formTurno.reset();
            bootstrap.Modal.getInstance(document.getElementById("modalTurno")).hide();
            cargarTurnosAsignados();
        } catch (error) {
            console.error("Error de conexión:", error);
            alert("No se pudo conectar con el servidor backend.");
        }
    });
});

async function cargarControladores() {
    try {
        const response = await fetch(`${API_URL}/controladores/`);
        listaControladoresCache = await response.json();
        
        const tbody = document.querySelector("#tablaControladores tbody");
        tbody.innerHTML = "";

        if (listaControladoresCache.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No hay controladores registrados.</td></tr>`;
            return;
        }

        listaControladoresCache.forEach(c => {
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

function prepararModalTurno() {
    const select = document.getElementById("selectControlador");
    select.innerHTML = "";

    if (listaControladoresCache.length === 0) {
        select.innerHTML = `<option value="">Debe registrar controladores primero</option>`;
        return;
    }

    listaControladoresCache.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = `${c.nombres} ${c.apellidos} (CC: ${c.identificacion})`;
        select.appendChild(opt);
    });

    // Poner fecha de hoy por defecto
    document.getElementById("fechaTurno").valueAsDate = new Date();
}

async function cargarTurnosAsignados() {
    try {
        const response = await fetch(`${API_URL}/turnos/`);
        const turnos = await response.json();
        
        const tbody = document.querySelector("#tablaTurnos tbody");
        tbody.innerHTML = "";

        if (turnos.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No hay turnos asignados en el cuadrante.</td></tr>`;
            return;
        }

        turnos.forEach(t => {
            const ctrl = listaControladoresCache.find(c => c.id === t.controlador_id);
            const nombreCtrl = ctrl ? `${ctrl.nombres} ${ctrl.apellidos} (CC: ${ctrl.identificacion})` : t.controlador_id;

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${t.fecha}</td>
                <td><span class="badge bg-primary">${t.turno_codigo}</span></td>
                <td>${nombreCtrl}</td>
                <td><span class="badge bg-success">Validado por Motor FAC</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error cargando turnos:", error);
    }
}

function descargarPDFOrdenServicio() {
    const fInicio = document.getElementById("pdfFechaInicio").value;
    const fFin = document.getElementById("pdfFechaFin").value;

    if (!fInicio || !fFin) {
        alert("Por favor seleccione la fecha de inicio y la fecha fin para el reporte PDF.");
        return;
    }

    const url = `${API_URL}/reportes/orden-servicio?fecha_inicio=${fInicio}&fecha_fin=${fFin}`;
    window.open(url, "_blank");
}