// app/static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado. Iniciando conexión con la API...");
    cargarBackends();
});

// Función para obtener los motores de backup disponibles y pintarlos en el HTML
async function cargarBackends() {
    const container = document.getElementById('backends-container');
    
    try {
        const response = await fetch('/api/v1/backends');
        if (!response.ok) {
            throw new Error(`Error en la API: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Motores de backup obtenidos:", data);
        
        // Limpiamos el texto de "Cargando motores..."
        container.innerHTML = '';

        // Si la API devuelve un diccionario o lista vacía
        if (!data || Object.keys(data).length === 0) {
            container.innerHTML = '<p>No hay motores de backup registrados.</p>';
            return;
        }

        // Iteramos sobre los motores recibidos (asumiendo que devuelve un array o un objeto con valores)
        const backendsList = Array.isArray(data) ? data : Object.values(data);
        
        backendsList.forEach(backend => {
            const backendEl = document.createElement('div');
            backendEl.style.padding = "10px";
            backendEl.style.marginTop = "10px";
            backendEl.style.backgroundColor = "#f9f9f9";
            backendEl.style.borderLeft = "4px solid #007bff";
            
            // Extraemos propiedades comunes (el esquema exacto depende de tu modelo Backend)
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