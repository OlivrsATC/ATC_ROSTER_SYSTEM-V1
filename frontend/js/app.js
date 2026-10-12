/**
 * ============================================================================
 * CONFIGURACIÓN GLOBAL Y VARIABLES DE ESTADO
 * ============================================================================
 */
const API_URL = "http://127.0.0.1:8000/api";
let listaControladoresCache = []; 
let controladorSeleccionadoId = null; 

/**
 * ============================================================================
 * INICIALIZACIÓN DE LA APLICACIÓN (DOM CARGADO)
 * ============================================================================
 */
document.addEventListener("DOMContentLoaded", () => {
    // 1. Poblar el selector de meses con un rango de 10 años y preseleccionar el actual
    poblarSelectMeses();

    // 2. Carga inicial de las tablas de controladores y el cuadrante mensual
    cargarControladores();
    cargarMatriz();

    // Vinculación del evento click para generar y descargar el reporte PDF de Orden de Servicio
    const btnDescargarPdf = document.getElementById("btnDescargarPdf");
    if (btnDescargarPdf) {
        btnDescargarPdf.addEventListener("click", descargarPDFOrdenServicio);
    }

    // Formulario de Registro de Nuevo Controlador
    const formControlador = document.getElementById("formControlador");
    if (formControlador) {
        formControlador.addEventListener("submit", async (e) => {
            e.preventDefault();

            const data = {
                identificacion: document.getElementById("identificacion").value,
                grado: document.getElementById("grado").value,
                numero_curso: document.getElementById("numero_curso").value,
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

    // Formulario de Asignación Individual de Turno
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

    // Formulario para Asignar una Autonomía a un Controlador
    const formAutonomia = document.getElementById("formAutonomia");
    if (formAutonomia) {
        formAutonomia.addEventListener("submit", async (e) => {
            e.preventDefault();
            const data = {
                controlador_id: controladorSeleccionadoId,
                tipo: document.getElementById("autTipo").value,
                posicion: document.getElementById("autPosicion").value,
                fecha_obtencion: document.getElementById("autFechaObt").value,
                fecha_vencimiento: document.getElementById("autFechaVen").value
            };

            try {
                const res = await fetch(`${API_URL}/autonomias/`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });

                if (res.ok) {
                    alert("Autonomía asignada con éxito.");
                    document.getElementById("autPosicion").value = "";
                    cargarAutonomiasModal(controladorSeleccionadoId);
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail}`);
                }
            } catch (error) {
                console.error("Error:", error);
            }
        });
    }

    // Formulario para Actualizar la Aptitud Psicofísica
    const formEditarAptitud = document.getElementById("formEditarAptitud");
    if (formEditarAptitud) {
        formEditarAptitud.addEventListener("submit", async (e) => {
            e.preventDefault();
            const ctrlId = document.getElementById("editCtrlId").value;
            const nuevaFecha = document.getElementById("editAptitudFecha").value;

            try {
                const res = await fetch(`${API_URL}/controladores/${ctrlId}/aptitud`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ aptitud_psicofisica_vencimiento: nuevaFecha })
                });

                if (res.ok) {
                    alert("¡Aptitud psicofísica actualizada con éxito!");
                    bootstrap.Modal.getInstance(document.getElementById("modalEditarAptitud")).hide();
                    cargarControladores();
                    cargarMatriz();
                } else {
                    const err = await res.json();
                    alert(`Error: ${err.detail}`);
                }
            } catch (error) {
                console.error("Error de conexión:", error);
                alert("No se pudo conectar con el servidor para actualizar la aptitud.");
            }
        });
    }
});

/**
 * ============================================================================
 * [NUEVA FUNCIÓN] POBLAR SELECTOR DE MESES (10 AÑOS Y MES ACTUAL)
 * ============================================================================
 */
function poblarSelectMeses() {
    const select = document.getElementById("selectMes");
    if (!select) return;
    select.innerHTML = "";

    const fechaActual = new Date();
    const anioActual = fechaActual.getFullYear();
    const mesActual = fechaActual.getMonth() + 1; // 1 (Enero) a 12 (Diciembre)

    const nombresMeses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    // Rango de 10 años a partir del año actual (ej. 2026 hasta 2035)
    for (let anio = anioActual; anio <= anioActual + 10; anio++) {
        for (let m = 1; m <= 12; m++) {
            const option = document.createElement("option");
            option.value = `${anio}-${m}`;
            option.textContent = `${nombresMeses[m - 1]} ${anio}`;

            // Preselecciona automáticamente el mes y año actual del sistema
            if (anio === anioActual && m === mesActual) {
                option.selected = true;
            }

            select.appendChild(option);
        }
    }
}

/**
 * ============================================================================
 * FUNCIONES DE GESTIÓN Y RENDERIZADO DE CONTROLADORES
 * ============================================================================
 */
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

        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);

        listaControladoresCache.forEach(c => {
            const fechaVen = new Date(c.aptitud_psicofisica_vencimiento + 'T00:00:00');
            const diffTime = fechaVen - hoy;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            let badgeAptitud = "bg-success"; 
            let styleAptitud = "";
            let textoAptitud = `${c.aptitud_psicofisica_vencimiento} (${diffDays} días)`;

            if (diffDays < 0) {
                badgeAptitud = "bg-dark";
                textoAptitud = `${c.aptitud_psicofisica_vencimiento} (VENCIDO hace ${Math.abs(diffDays)} días)`;
            } else if (diffDays < 15) {
                badgeAptitud = "bg-danger text-white fw-bold";
                textoAptitud = `${c.aptitud_psicofisica_vencimiento} (¡Vence en ${diffDays} días!)`;
            } else if (diffDays <= 30) {
                badgeAptitud = "";
                styleAptitud = "background-color: #fd7e14; color: white; font-weight: bold;";
                textoAptitud = `${c.aptitud_psicofisica_vencimiento} (¡Vence en ${diffDays} días!)`;
            }

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${c.identificacion}</td>
                <td class="fw-bold"><span class="badge bg-dark me-1">${c.grado}</span> ${c.apellidos} ${c.nombres} <small class="text-muted">(Crs ${c.numero_curso || 'N/A'})</small></td>
                <td>${c.email}</td>
                <td><span class="badge bg-secondary">${c.rol}</span></td>
                <td><span class="badge ${badgeAptitud}" style="${styleAptitud}">${textoAptitud}</span></td>
                <td><span class="badge ${c.activo ? 'bg-success' : 'bg-danger'}">${c.activo ? 'Activo' : 'Inactivo'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="abrirModalEditarAptitud('${c.id}', '${c.grado}. ${c.apellidos} ${c.nombres}', '${c.aptitud_psicofisica_vencimiento}')" title="Actualizar Aptitud Psicofísica">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary me-1" onclick="abrirModalAutonomias('${c.id}', '${c.grado}. ${c.apellidos} ${c.nombres}')" title="Gestionar Autonomías">
                        <i class="fa-solid fa-shield-halved"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="eliminarControlador('${c.id}')" title="Eliminar">
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

/**
 * ============================================================================
 * FUNCIONES DEL CUADRANTE MENSUAL Y MATRIZ OPERATIVA
 * ============================================================================
 */
async function cargarMatriz() {
    const selectMes = document.getElementById("selectMes");
    if (!selectMes) return;
    
    // Extraer año y mes seleccionados dinámicamente del select (formato: "YYYY-M")
    const [anio, mes] = selectMes.value.split("-");

    try {
        const res = await fetch(`${API_URL}/cuadrante/matriz?anio=${anio}&mes=${mes}`);
        const data = await res.json();

        const thead = document.getElementById("headerMatriz");
        const tbody = document.getElementById("bodyMatriz");

        let headerHtml = `<tr><th rowspan="2" class="align-middle">#</th><th rowspan="2" class="align-middle text-start">CONTROLADOR</th>`;
        data.dias_info.forEach(d => {
            const bgHeader = d.es_especial ? "bg-warning bg-opacity-25" : "";
            headerHtml += `<th class="${bgHeader}">${d.dia}</th>`;
        });
        headerHtml += `</tr>`;

        headerHtml += `<tr>`;
        data.dias_info.forEach(d => {
            const bgSub = d.es_especial ? "bg-warning bg-opacity-25 text-dark" : "bg-secondary text-white";
            headerHtml += `<th class="${bgSub} small" style="font-size: 0.7rem;">${d.letra}</th>`;
        });
        headerHtml += `</tr>`;
        thead.innerHTML = headerHtml;

        tbody.innerHTML = "";
        if (!data.filas || data.filas.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${data.total_dias + 2}" class="text-center text-muted py-3">No hay personal registrado en la matriz. Haz clic en "Generar Automático Mes".</td></tr>`;
            return;
        }

        const opcionesTurnos = ["", "SM", "ST", "SD","TM","TT","TD","TN","AM","AT","AD","GM","GT","GD","OM","OT","OD","ON", "VEL", "CP", "DISP", "VAC", "HU", "ENTTO", "REEN", "PAT", "INS"];

        data.filas.forEach(f => {
            let rowHtml = `<tr>
                <td class="fw-bold bg-light">${f.numero_orden}</td>
                <td class="text-start fw-bold text-nowrap">${f.nombre_completo}</td>`;
            
            data.dias_info.forEach(d => {
                const codigoActual = f.dias[d.dia] || "";
                
                let selectHtml = `<select class="form-select form-select-sm border-0 bg-transparent text-center fw-bold p-0 shadow-none" style="font-size: 0.75rem; min-width: 45px; appearance: none; -webkit-appearance: none; background-image: none;" onchange="actualizarCelda('${f.id}', ${anio}, ${mes}, ${d.dia}, this.value)">`;
                opcionesTurnos.forEach(opt => {
                    const selected = opt === codigoActual ? "selected" : "";
                    selectHtml += `<option value="${opt}" ${selected}>${opt || '-'}</option>`;
                });
                selectHtml += `</select>`;

                let bgClass = d.es_especial ? "bg-warning bg-opacity-10" : "bg-white";
                if (codigoActual === "VEL") bgClass = "bg-warning bg-opacity-25";
                else if (["SM", "AM"].includes(codigoActual)) bgClass = "bg-primary bg-opacity-25";
                else if (["ST", "AT"].includes(codigoActual)) bgClass = "bg-info bg-opacity-25";
                else if (["TN", "ON"].includes(codigoActual)) bgClass = "bg-danger bg-opacity-25";
                else if (codigoActual === "DISP") bgClass = "bg-success bg-opacity-25";
                else if (codigoActual === "VAC") bgClass = "bg-secondary bg-opacity-25";

                rowHtml += `<td class="${bgClass} p-0">${selectHtml}</td>`;
            });
            rowHtml += `</tr>`;
            tbody.innerHTML += rowHtml;
        });
    } catch (e) {
        console.error("Error cargando matriz:", e);
    }
}

/**
 * Función para limpiar/deshacer toda la programación automática del mes en curso
 */
async function deshacerCuadranteAutomatico() {
    const selectMes = document.getElementById("selectMes");
    const [anio, mes] = selectMes.value.split("-");

    if (!confirm(`¿Está seguro de deshacer y borrar toda la programación asignada para este periodo?`)) return;

    try {
        const res = await fetch(`${API_URL}/cuadrante/limpiar?anio=${anio}&mes=${mes}`, { method: "DELETE" });
        const data = await res.json();
        alert(data.mensaje || "Se ha limpiado la programación del mes con éxito.");
        cargarMatriz();
    } catch (e) {
        console.error("Error:", e);
        alert("Error al conectar con el servidor para deshacer la programación.");
    }
}

/**
 * Actualiza una celda específica del cuadrante al cambiar de valor en el select
 */
async function actualizarCelda(controladorId, anio, mes, dia, nuevoCodigo) {
    const fechaStr = `${anio}-${String(mes).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
    
    try {
        const res = await fetch(`${API_URL}/cuadrante/celda`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                controlador_id: controladorId,
                fecha: fechaStr,
                turno_codigo: nuevoCodigo
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`⚠️ Restricción operativa: ${err.detail}`);
            cargarMatriz();
            return;
        }

        cargarMatriz();
    } catch (e) {
        console.error("Error actualizando celda:", e);
        alert("Error de conexión al actualizar la celda.");
    }
}

/**
 * Ejecuta el generador automático de turnos del mes evaluando el motor de reglas
 */
async function generarCuadranteAutomatico() {
    const selectMes = document.getElementById("selectMes");
    const [anio, mes] = selectMes.value.split("-");

    if (!confirm("¿Desea generar automáticamente la programación para todo el mes evaluando el motor de reglas de la FAC?")) return;

    try {
        const res = await fetch(`${API_URL}/cuadrante/generar?anio=${anio}&mes=${mes}`, { method: "POST" });
        const data = await res.json();
        alert(data.mensaje || "Cuadrante generado con éxito.");
        cargarMatriz();
    } catch (e) {
        console.error("Error:", e);
        alert("Error al generar el cuadrante.");
    }
}

/**
 * ============================================================================
 * GESTIÓN DE AUTONOMÍAS Y MODALES DE CONTROLADORES
 * ============================================================================
 */
async function abrirModalAutonomias(ctrlId, nombreCompleto) {
    controladorSeleccionadoId = ctrlId;
    document.getElementById("nombreCtrlModal").textContent = nombreCompleto;
    document.getElementById("autCtrlId").value = ctrlId;
    
    document.getElementById("autFechaObt").valueAsDate = new Date();
    document.getElementById("autFechaVen").value = "2028-04-20";

    await cargarAutonomiasModal(ctrlId);
    
    const modal = new bootstrap.Modal(document.getElementById("modalAutonomias"));
    modal.show();
}

async function cargarAutonomiasModal(ctrlId) {
    try {
        const res = await fetch(`${API_URL}/autonomias/${ctrlId}`);
        const autonomias = await res.json();
        
        const tbody = document.querySelector("#tablaAutonomiasModal tbody");
        tbody.innerHTML = "";

        if (autonomias.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No tiene autonomías asignadas.</td></tr>`;
            return;
        }

        autonomias.forEach(a => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><span class="badge bg-primary">${a.tipo}</span></td>
                <td>${a.posicion}</td>
                <td>${a.fecha_obtencion}</td>
                <td>${a.fecha_vencimiento}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="eliminarAutonomia('${a.id}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error cargando autonomías:", e);
    }
}

async function eliminarAutonomia(autId) {
    if (!confirm("¿Eliminar esta autonomía?")) return;
    try {
        const res = await fetch(`${API_URL}/autonomias/${autId}`, { method: "DELETE" });
        if (res.ok) {
            cargarAutonomiasModal(controladorSeleccionadoId);
        }
    } catch (e) {
        console.error("Error:", e);
    }
}

function abrirModalEditarAptitud(ctrlId, nombreCompleto, fechaActual) {
    document.getElementById("editCtrlId").value = ctrlId;
    document.getElementById("labelNombreCtrlApt").textContent = `Controlador: ${nombreCompleto}`;
    document.getElementById("editAptitudFecha").value = fechaActual;

    const modal = new bootstrap.Modal(document.getElementById("modalEditarAptitud"));
    modal.show();
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

/**
 * ============================================================================
 * EXPORTACIÓN Y REPORTES PDF
 * ============================================================================
 */
function descargarPDFOrdenServicio() {
    const fInicio = document.getElementById("pdfFechaInicio").value;
    const fFin = document.getElementById("pdfFechaFin").value;
    const asesor = encodeURIComponent(document.getElementById("asesorNav").value);
    const gruco = encodeURIComponent(document.getElementById("cmdGruco").value);
    const esnav = encodeURIComponent(document.getElementById("cmdEsnav").value);

    if (!fInicio || !fFin) {
        alert("Por favor seleccione la fecha de inicio y la fecha fin para el reporte PDF.");
        return;
    }

    const url = `${API_URL}/reportes/orden-servicio?fecha_inicio=${fInicio}&fecha_fin=${fFin}&asesor_nav=${asesor}&comandante_gruco=${gruco}&comandante_esnav=${esnav}`;
    window.open(url, "_blank");
}