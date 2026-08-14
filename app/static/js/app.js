// app/static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado. Iniciando conexión con la API...");[cite: 7]
    cargarBackends();[cite: 7]
    initWebSocketProgress();
});

// Función para obtener los motores de backup disponibles y pintarlos en el HTML[cite: 7]
async function cargarBackends() {
    const container = document.getElementById('backends-container');[cite: 7]
    if (!container) return;[cite: 7]
    
    try {
        const response = await fetch('/api/v1/backends');[cite: 7]
        if (!response.ok) {
            throw new Error(`Error en la API: ${response.status}`);[cite: 7]
        }
        
        const data = await response.json();[cite: 7]
        console.log("Motores de backup obtenidos:", data);[cite: 7]
        
        container.innerHTML = '';[cite: 7]

        if (!data || Object.keys(data).length === 0) {
            container.innerHTML = '<p>No hay motores de backup registrados.</p>';[cite: 7]
            return;
        }

        const backendsList = Array.isArray(data) ? data : Object.values(data);[cite: 7]
        
        backendsList.forEach(backend => {
            const backendEl = document.createElement('div');[cite: 7]
            backendEl.style.padding = "10px";[cite: 7]
            backendEl.style.marginTop = "10px";[cite: 7]
            backendEl.style.backgroundColor = "#f9f9f9";[cite: 7]
            backendEl.style.borderLeft = "4px solid #007bff";[cite: 7]
            
            const nombre = backend.name || backend.id || 'Motor Desconocido';[cite: 7]
            const estado = backend.status || 'Activo';[cite: 7]
            
            backendEl.innerHTML = `
                <h3 style="margin:0 0 5px 0;">🔌 ${nombre}</h3>
                <p style="margin:0;">Estado de integración: <strong>${estado}</strong></p>
            `;[cite: 7]
            container.appendChild(backendEl);[cite: 7]
        });
        
    } catch (error) {
        console.error("Fallo al cargar los motores de backup:", error);[cite: 7]
        container.innerHTML = `<p style="color: red;">Error al cargar los motores: ${error.message}</p>`;[cite: 7]
    }
}

// Función global auxiliar para ejecutar la restauración 1-Click[cite: 7]
async function solicitarRestauracion(snapshotId, appName) {
    try {
        const response = await fetch('/api/v1/restore/execute', {
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
        console.log("Restauración iniciada con éxito:", data);
        return data;
    } catch (error) {
        console.error("Error al enviar solicitud de restauración:", error);
        alert("No se pudo iniciar la restauración: " + error.message);
    }
}

// Gestión del WebSocket para ocultar la barra flotante al completarse la restauración
function initWebSocketProgress() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress`;
    
    const ws = new WebSocket(wsUrl);

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === "restore_complete" || data.status === "COMPLETED") {
                const progressBar = document.querySelector('.progress-bar, .bg-primary, [role="progressbar"]');
                if (progressBar) progressBar.style.width = "100%";
                
                setTimeout(() => {
                    const floatingContainer = document.querySelector('.progress')?.closest('div.card, div.shadow, div');
                    if (floatingContainer) {
                        floatingContainer.style.display = 'none';
                    }
                    window.location.reload();
                }, 2000);
            }
        } catch (err) {
            console.error("Error al procesar mensaje de WebSocket:", err);
        }
    };

    ws.onclose = function() {
        setTimeout(initWebSocketProgress, 5000);
    };
}