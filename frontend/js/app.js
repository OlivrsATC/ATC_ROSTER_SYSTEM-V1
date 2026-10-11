const API_URL = "http://127.0.0.1:8000/api";
let listaControladoresCache = [];

document.addEventListener("DOMContentLoaded", () => {
    cargarControladores();
    cargarMatriz();

    // Formulario Registro Controlador
    const formControlador = document.getElementById("formControlador");
    if (formControlador) {
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
                cargarMatriz();
            } catch (error) {
                console.error("Error de conexión:", error);
                alert("No se pudo conectar con el servidor backend.");
            }
        });
    }

    // Formulario Asignación Individual de Turno
    const formTurno = document.getElementById("formTurno");
    if (formTurno) {
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
                cargarMatriz();
            } catch (error) {
                console.error("Error de conexión:", error);
                alert("No se pudo conectar con el servidor backend.");
            }
        });
    }
});

async function cargarControladores() {
    try {
        const response = await fetch(`${API_URL}/controladores/`);
        listaControladoresCache = await response.json();
        
        const tbody = document.querySelector("#tablaControladores tbody");
        if (!tbody) return;
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

async function cargarMatriz() {
    const mesSelect = document.getElementById("selectMes");
    if (!mesSelect) return;
    const mes = mesSelect.value;

    try {
        const res = await fetch(`${API_URL}/cuadrante/matriz?anio=2026&mes=${mes}`);
        const data = await res.json();

        const thead = document.getElementById("headerMatriz");
        const tbody = document.getElementById("bodyMatriz");

        // Cabecera de días (1 al 30/31)
        let headerHtml = `<tr><th>#</th><th class="text-start">CONTROLADOR</th>`;
        for (let d = 1; d <= data.total_dias; d++) {
            headerHtml += `<th>${d}</th>`;
        }
        headerHtml += `</tr>`;
        thead.innerHTML = headerHtml;

        // Filas del personal
        tbody.innerHTML = "";
        if (!data.filas || data.filas.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${data.total_dias + 2}" class="text-center text-muted py-3">No hay datos en la matriz para este mes. Haz clic en "Generar Automático Mes".</td></tr>`;
            return;
        }

        data.filas.forEach(f => {
            let rowHtml = `<tr>
                <td class="fw-bold bg-light">${f.numero_orden}</td>
                <td class="text-start fw-bold">${f.nombre_completo}</td>`;
            
            for (let d = 1; d <= data.total_dias; d++) {
                const codigo = f.dias[d] || "";
                let badgeClass = "badge bg-light text-dark border";
                if (codigo === "VEL") badgeClass = "badge-vel";
                else if (["SM", "AM"].includes(codigo)) badgeClass = "badge-sm";
                else if (["ST", "AT"].includes(codigo)) badgeClass = "badge-st";
                else if (["TN", "ON"].includes(codigo)) badgeClass = "badge-tn";
                else if (codigo === "DISP") badgeClass = "badge-disp";
                else if (codigo === "VAC") badgeClass = "badge-vac";

                rowHtml += `<td><span class="${badgeClass} px-1 py-1 d-block">${codigo}</span></td>`;
            }
            rowHtml += `</tr>`;
            tbody.innerHTML += rowHtml;
        });
    } catch (e) {
        console.error("Error cargando matriz:", e);
    }
}

async function generarCuadranteAutomatico() {
    const mes = document.getElementById("selectMes").value;
    if (!confirm("¿Desea generar automáticamente la programación para todo el mes evaluando el motor de reglas de la FAC?")) return;

    try {
        const res = await fetch(`${API_URL}/cuadrante/generar?anio=2026&mes=${mes}`, { method: "POST" });
        const data = await res.json();
        alert(data.mensaje || "Cuadrante generado con éxito.");
        cargarMatriz();
    } catch (e) {
        console.error("Error:", e);
        alert("Error al generar el cuadrante.");
    }
}

function prepararModalTurno() {
    const select = document.getElementById("selectControlador");
    if (!select) return;
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

    document.getElementById("fechaTurno").valueAsDate = new Date();
}

async function eliminarControlador(id) {
    if (!confirm("¿Está seguro de eliminar este controlador?")) return;

    try {
        const response = await fetch(`${API_URL}/controladores/${id}`, { method: "DELETE" });
        if (response.ok) {
            alert("Controlador eliminado.");
            cargarControladores();
            cargarMatriz();
        } else {
            alert("Error al eliminar el controlador.");
        }
    } catch (error) {
        console.error("Error:", error);
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