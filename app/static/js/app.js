// Renderizado robusto de Historial
function renderHistoryTable(logs) {
    const tbody = document.getElementById('historyTableBody') || document.querySelector('#historyModal table tbody');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay registros de ejecución.</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => {
        const fecha = log.fecha || log.date || log.time || (log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Fecha desconocida');
        const duracion = log.duracion || log.duration || log.elapsed || '1.0s';
        const estado = (log.estado === 'success' || log.status === 'success') 
            ? '<span class="badge bg-success">Éxito</span>' 
            : '<span class="badge bg-danger">Error</span>';

        return `
            <tr>
                <td>${fecha}</td>
                <td>${log.tipo || log.type || 'Backup'}</td>
                <td><code class="text-pink">${log.objetivo || log.target || 'Sistema'}</code></td>
                <td>${estado}</td>
                <td>${duracion}</td>
            </tr>
        `;
    }).join('');
}

// Renderizado de Copias Disponibles para Restauración
async function loadRestoreBackups() {
    const container = document.getElementById('restoreListContainer') || document.querySelector('#restoreModal .modal-body');
    if (!container) return;

    try {
        const response = await fetch('/api/v1/backups/list');
        const backups = await response.json();

        if (!backups || backups.length === 0) {
            container.innerHTML = '<div class="alert alert-info text-center m-3">No se han encontrado copias de seguridad en el disco seleccionado.</div>';
            return;
        }

        container.innerHTML = `
            <div class="list-group">
                ${backups.map(b => `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1 fw-bold">${b.filename}</h6>
                            <small class="text-muted">Aplicación: <b>${b.app_name}</b> | Fecha: ${b.fecha} | Tamaño: ${b.size}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-primary" onclick="restoreBackup('${b.file_path}')">Restaurar</button>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        console.error("Error al cargar copias de restauración:", e);
    }
}