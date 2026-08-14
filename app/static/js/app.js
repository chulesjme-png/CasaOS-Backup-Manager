// app/static/js/app.js

// Interceptor global para atrapar el momento exacto en que la API responde al restaurar
const originalFetch = window.fetch;
window.fetch = async function(...args) {
    const url = args[0];
    const response = await originalFetch.apply(this, args);
    
    // Si la petición a la ruta de restauración finaliza con éxito
    if (typeof url === 'string' && url.includes('/api/v1/backups/restore')) {
        if (response.ok) {
            console.log("Restauración finalizada con éxito. Forzando limpieza de interfaz...");
            setTimeout(() => {
                destruirBarraProgresoForzosa();
                window.location.reload();
            }, 600);
        }
    }
    return response;
};

document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado. Activando monitor de limpieza visual...");
    cargarBackends();
    initWebSocketProgress();
    destruirBarraProgresoForzosa();

    // Vigilar continuamente el DOM por si el framework frontend vuelve a pintar la barra
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(() => {
            destruirBarraProgresoForzosa();
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
});

// Función agresiva para buscar y destruir cualquier rastro de la barra de progreso de restauración
function destruirBarraProgresoForzosa() {
    document.querySelectorAll('div, section, aside').forEach(el => {
        const texto = el.innerText || "";
        if (
            texto.includes("Copia: Restauración") || 
            texto.includes("Iniciando despliegue") || 
            (texto.includes("10%") && texto.includes("Restauración"))
        ) {
            el.style.display = 'none';
            el.remove();
        }
    });
}

// Función para obtener los motores de backup disponibles
async function cargarBackends() {
    const container = document.getElementById('backends-container');
    if (!container) return;
    
    try {
        const response = await originalFetch('/api/v1/backends');
        if (!response.ok) throw new Error(`Error en la API: ${response.status}`);
        
        const data = await response.json();
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
    }
}

// Gestión del WebSocket por seguridad
function initWebSocketProgress() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress`;
    
    const ws = new WebSocket(wsUrl);
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "restore_complete" || data.status === "COMPLETED") {
                destruirBarraProgresoForzosa();
                window.location.reload();
            }
        } catch (err) {}
    };
    ws.onclose = function() {
        setTimeout(initWebSocketProgress, 5000);
    };
}