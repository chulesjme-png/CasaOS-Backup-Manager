// app/static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado. Iniciando conexión con la API...");
    cargarBackends();
    initWebSocketProgress();
});

// Función para obtener los motores de backup disponibles y pintarlos en el HTML
async function cargarBackends() {
    const container = document.getElementById('backends-container');
    if (!container) return;
    
    try {
        const response = await fetch('/api/v1/backends');
        if (!response.ok) {
            throw new Error(`Error en la API: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Motores de backup obtenidos:", data);
        
        container.innerHTML = '';

        if (!data || Object.keys(data).length === 0) {
            container.innerHTML = '<p>No hay motores de backup registrados.</p>';
            return;
        }

        const backendsList = Array.isArray(data) ? data : Object.values(data);
        
        backendsList.forEach(backend => {
            const backendEl = document.createElement('div');
            backendEl.style.padding = "10px";
            backendEl.style.marginTop = "10px";
            backendEl.style.backgroundColor = "#f9f9f9";
            backendEl.style.borderLeft = "4px solid #007bff";
            
            const nombre = backend.name || backend.id || 'Motor Desconocido';
            const estado = backend.status || 'Activo';
            
            backendEl.innerHTML = `
                <h3 style="margin:0 0 5px 0;">🔌 ${nombre}</h3>
                <p style="margin:0;">Estado de integración: <strong>${estado}</strong></p>
            `;
            container.appendChild(backendEl);
        });
        
    } catch (error) {
        console.error("Fallo al cargar los motores de backup:", error);
        container.innerHTML = `<p style="color: red;">Error al cargar los motores: ${error.message}</p>`;
    }
}

// Función global auxiliar para ejecutar la restauración 1-Click
async function solicitarRestauracion(snapshotId, appName) {
    try {
        const response = await fetch('/api/v1/backups/restore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                snapshot_id: snapshotId,
                app_name: appName
            })
        });

        if (!response.ok) {
            throw new Error(`Respuesta de red KO (${response.status})`);
        }

        const data = await response.json();
        console.log("Restauración iniciada/completada con éxito:", data);

        // Forzar limpieza y cierre de la notificación flotante al terminar con éxito
        finalizarBarraProgresoVisual();

        return data;
    } catch (error) {
        console.error("Error al enviar solicitud de restauración:", error);
        alert("No se pudo iniciar la restauración: " + error.message);
        finalizarBarraProgresoVisual();
    }
}

// Función para completar visualmente la barra y ocultarla
function finalizarBarraProgresoVisual() {
    // Buscar cualquier barra de progreso y ponerla al 100%
    document.querySelectorAll('.progress-bar, [role="progressbar"]').forEach(bar => {
        bar.style.width = "100%";
    });

    // Actualizar textos de estado si existen
    document.querySelectorAll('div').forEach(el => {
        if (el.textContent && el.textContent.includes("Iniciando despliegue")) {
            el.textContent = "¡Restauración completada con éxito!";
        }
    });

    // Ocultar contenedor flotante y recargar tras 1.5 segundos
    setTimeout(() => {
        document.querySelectorAll('div').forEach(box => {
            const style = window.getComputedStyle(box);
            if (style.position === 'fixed' || box.style.position === 'fixed') {
                if (box.innerHTML.includes("Restauración") || box.innerHTML.includes("despliegue") || box.innerHTML.includes("10%")) {
                    box.style.display = 'none';
                }
            }
        });
        window.location.reload();
    }, 1500);
}

// Gestión del WebSocket para sincronización en tiempo real adicional
function initWebSocketProgress() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress`;
    
    const ws = new WebSocket(wsUrl);

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "restore_complete" || data.status === "COMPLETED") {
                finalizarBarraProgresoVisual();
            }
        } catch (err) {
            console.error("Error al procesar mensaje de WebSocket:", err);
        }
    };

    ws.onclose = function() {
        setTimeout(initWebSocketProgress, 5000);
    };
}