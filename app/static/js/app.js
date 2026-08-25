// 1. Cargar Historial de Ejecuciones
async function loadHistory() {
    try {
        const res = await fetch('/api/v1/executions?limit=50');
        const logs = await res.json();
        const tbody = document.getElementById('historyTableBody') || document.querySelector('#historyModal tbody');
        
        if (!tbody) return;

        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay registros de ejecución.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(log => {
            const fecha = log.fecha || log.date || log.created_at || 'Reciente';
            const duracion = log.duracion || log.duration || log.elapsed || '0.3s';
            const objetivo = log.objetivo || log.target || log.app_name || 'Sistema';
            const estado = (log.estado === 'success' || log.status === 'success') 
                ? '<span class="badge bg-success">Éxito</span>' 
                : '<span class="badge bg-danger">Error</span>';

            return `
                <tr>
                    <td>${fecha}</td>
                    <td>${log.tipo || log.type || 'Backup'}</td>
                    <td><code class="text-pink">${objetivo}</code></td>
                    <td>${estado}</td>
                    <td>${duracion}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Error cargando historial:", e);
    }
}

// 2. Cargar Copias para Restaurar
async function loadRestoreBackups() {
    const container = document.getElementById('restoreListContainer') || document.querySelector('#restoreModal .modal-body');
    if (!container) return;

    try {
        const response = await fetch('/api/v1/backups/list');
        const backups = await response.json();

        if (!backups || backups.length === 0) {
            container.innerHTML = '<div class="alert alert-info text-center m-3">No se han encontrado copias de seguridad.</div>';
            return;
        }

        container.innerHTML = `
            <div class="list-group">
                ${backups.map(b => `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div class="text-start">
                            <h6 class="mb-1 fw-bold text-dark">${b.filename || b.name}</h6>
                            <small class="text-muted">App: <b class="text-primary">${b.app_name || b.target || 'App'}</b> | Fecha: ${b.fecha || b.date} | Tamaño: ${b.size_str || b.size}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="restoreBackup('${b.file_path || b.path}')">Restaurar</button>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        console.error("Error cargando copias de restauración:", e);
    }
}