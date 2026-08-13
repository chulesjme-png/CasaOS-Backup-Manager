/**
 * CasaOS Backup Manager - WebSocket Progress Client
 * Gestiona la conexión en tiempo real para visualizar el progreso
 * de copias de seguridad y restauraciones.
 */

(function () {
    let progressSocket = null;
    let pingInterval = null;

    // Detectar si el backend se sirve con HTTP o HTTPS
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/progress`;

    /**
     * Garantiza que exista el contenedor de la barra de progreso en el DOM.
     * Si no existe en el HTML, lo crea dinámicamente en la esquina inferior derecha.
     */
    function ensureProgressUI() {
        if (document.getElementById('ws-progress-toast')) return;

        const toastHTML = `
            <div id="ws-progress-toast" class="hidden fixed bottom-6 right-6 z-50 w-96 bg-gray-900 text-white rounded-xl shadow-2xl border border-gray-700 p-4 transition-all duration-300 transform translate-y-0">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center space-x-2">
                        <span id="ws-job-icon" class="animate-pulse text-blue-400">⚡</span>
                        <h4 id="ws-job-title" class="text-sm font-semibold text-gray-200">Procesando Tarea...</h4>
                    </div>
                    <span id="ws-progress-percent" class="text-xs font-bold bg-blue-600 text-white px-2 py-0.5 rounded-full">0%</span>
                </div>
                
                <!-- Barra de Progreso Fondo -->
                <div class="w-full bg-gray-700 h-2.5 rounded-full overflow-hidden mb-2">
                    <!-- Relleno de la Barra -->
                    <div id="ws-progress-bar" class="bg-gradient-to-r from-blue-500 to-emerald-400 h-2.5 rounded-full transition-all duration-300 ease-out" style="width: 0%"></div>
                </div>

                <!-- Mensaje Estado -->
                <p id="ws-progress-message" class="text-xs text-gray-400 truncate">Iniciando proceso...</p>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', toastHTML);
    }

    /**
     * Actualiza los valores de la barra de progreso en la interfaz.
     */
    function updateProgressUI(jobId, percentage, message) {
        ensureProgressUI();

        const toast = document.getElementById('ws-progress-toast');
        const bar = document.getElementById('ws-progress-bar');
        const percentText = document.getElementById('ws-progress-percent');
        const msgText = document.getElementById('ws-progress-message');
        const titleText = document.getElementById('ws-job-title');

        if (!toast) return;

        // Mostrar el Toast
        toast.classList.remove('hidden');

        // Formatear Título según la tarea
        if (jobId.startsWith('backup_')) {
            titleText.innerText = `Copia: ${jobId.replace('backup_', '')}`;
        } else if (jobId.startsWith('restore_')) {
            titleText.innerText = `Restaurando: ${jobId.replace('restore_', '')}`;
        } else {
            titleText.innerText = `Tarea en ejecución`;
        }

        // Actualizar porcentaje y mensaje
        bar.style.width = `${percentage}%`;
        percentText.innerText = `${percentage}%`;
        msgText.innerText = message;

        // Gestión de colores en caso de error o finalización
        if (message.toLowerCase().includes('error')) {
            bar.classList.remove('from-blue-500', 'to-emerald-400');
            bar.classList.add('bg-red-500');
            percentText.classList.remove('bg-blue-600');
            percentText.classList.add('bg-red-600');
        } else {
            bar.classList.remove('bg-red-500');
            bar.classList.add('from-blue-500', 'to-emerald-400');
            percentText.classList.remove('bg-red-600');
            percentText.classList.add('bg-blue-600');
        }

        // Si la tarea llega al 100% o da error, ocultar suavemente tras unos segundos
        if (percentage === 100 || percentage === 0 && message.toLowerCase().includes('error')) {
            setTimeout(() => {
                toast.classList.add('hidden');
                // Resetear ancho para futuras tareas
                setTimeout(() => { bar.style.width = '0%'; }, 300);
            }, 4000);
        }
    }

    /**
     * Inicia y mantiene la conexión WebSocket con el servidor FastAPI.
     */
    function initWebSocket() {
        progressSocket = new WebSocket(wsUrl);

        progressSocket.onopen = () => {
            console.log("🟢 [WebSocket] Canal de progreso conectado.");

            // Mantener viva la conexión enviando PING cada 20 segundos
            clearInterval(pingInterval);
            pingInterval = setInterval(() => {
                if (progressSocket.readyState === WebSocket.OPEN) {
                    progressSocket.send("ping");
                }
            }, 20000);
        };

        progressSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Ejemplo payload: { job_id: "backup_plex", percentage: 50, message: "Comprimiendo..." }
                if (data && typeof data.percentage === 'number') {
                    updateProgressUI(data.job_id, data.percentage, data.message);
                }
            } catch (err) {
                // Mensajes de texto simples o pings
            }
        };

        progressSocket.onclose = () => {
            console.warn("🔴 [WebSocket] Conexión perdida. Reintentando en 3 segundos...");
            clearInterval(pingInterval);
            setTimeout(initWebSocket, 3000);
        };

        progressSocket.onerror = (error) => {
            console.error("⚠️ [WebSocket] Error detectado:", error);
            progressSocket.close();
        };
    }

    // Arrancar WebSocket al cargar la página
    document.addEventListener('DOMContentLoaded', () => {
        ensureProgressUI();
        initWebSocket();
    });
})();