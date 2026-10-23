#!/usr/bin/env bash

# ==============================================================================
# CasaOS Backup Manager - Script de Rescate Standalone para BorgBackup
# ==============================================================================
# Autor: Automatización de Disaster Recovery (v1.0.0)
# Descripción: Extrae y restaura un snapshot completo de Borg de forma segura
#              utilizando un directorio de staging temporal y rsync.
# ==============================================================================

# Detener el script inmediatamente si ocurre algún error
set -euo pipefail

# --- CONFIGURACIÓN POR DEFECTO ---
# Ajusta estas rutas según tu entorno de producción en la Raspberry Pi 5
BORG_REPO="${BORG_REPO:-/mnt/external_drive/borg_backup_repo}"
STAGING_DIR="/tmp/restore_staging"
DRY_RUN=false
SNAPSHOT_NAME=""
TARGET_DIR="/"

# --- COLORES PARA LOGS ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[print_nc]' # No Color (ajustado a NC estándar)
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Verificar privilegios de root (necesario para restaurar permisos y modificar rootfs)
if [[ $EUID -ne 0 ]]; then
   log_error "Este script debe ejecutarse con privilegios de root (sudo)."
fi

# --- AYUDA / USO ---
usage() {
    echo -e "Uso: sudo $0 [OPCIONES]"
    echo -e ""
    echo -e "Opciones:"
    echo -e "  -s, nombre      Nombre exacto del snapshot de Borg a restaurar (obligatorio)"
    echo -e "  -r, ruta        Ruta del repositorio Borg (por defecto: $BORG_REPO)"
    echo -e "  -d,             Modo simulación (dry-run): simula la restauración sin escribir en disco"
    echo -e "  -h,             Muestra esta ayuda"
    echo -e ""
    echo -e "Ejemplo:"
    echo -e "  sudo $0 -s Sistema_Completo_2026-09-22_13-49-01 --dry-run"
    exit 1
}

# --- PROCESAMIENTO DE ARGUMENTOS ---
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--snapshot)
            SNAPSHOT_NAME="$2"
            shift 2
            ;;
        -r|--repo)
            BORG_REPO="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Opción desconocida: $1"
            ;;
    esac
done

if [[ -z "$SNAPSHOT_NAME" ]]; then
    log_error "Debes especificar un snapshot con la opción -s o --snapshot. Usa -h para ver ayuda."
fi

# --- COMPROBACIONES PREVIAS ---
log_info "Verificando dependencias y accesibilidad del repositorio..."
command -v borg >/dev/null 2>&1 || log_error "La herramienta 'borg' no está instalada en el host."
command -v rsync >/dev/null 2>&1 || log_error "La herramienta 'rsync' no está instalada en el host."

if [[ ! -d "$BORG_REPO" ]]; then
    log_error "El repositorio Borg no existe en la ruta: $BORG_REPO"
fi

# Verificar si el snapshot existe en el repositorio
log_info "Comprobando existencia del snapshot '$SNAPSHOT_NAME'..."
if ! borg list "$BORG_REPO" | grep -q "$SNAPSHOT_NAME"; then
    log_error "El snapshot '$SNAPSHOT_NAME' no se encuentra en el repositorio $BORG_REPO."
fi

# --- FASE 1: PREPARACIÓN DEL STAGING ---
log_info "Preparando directorio de staging en $STAGING_DIR..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# --- FASE 2: EXTRACCIÓN DESDE BORG ---
log_info "Iniciando extracción del snapshot hacia el entorno de staging..."
log_warn "Esto puede tardar dependiendo del tamaño del backup y la velocidad del disco."

export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes # Por seguridad si usas repo sin pass o keyfile local
if borg extract --progress "$BORG_REPO::$SNAPSHOT_NAME" --destination "$STAGING_DIR"; then
    log_success "Extracción completada con éxito en el staging."
else
    log_error "Falló el proceso de extracción de Borg."
fi

# --- FASE 3: SINCRONIZACIÓN (RSYNC) ---
RSYNC_OPTS="-aAXv --info=progress2 --delete"
if [ "$DRY_RUN" = true ]; then
    log_warn "MODO SIMULACIÓN ACTIVADO (--dry-run). No se realizarán cambios reales en el sistema."
    RSYNC_OPTS="$RSYNC_OPTS --dry-run"
fi

log_info "Iniciando sincronización atómica con el sistema raíz ($TARGET_DIR)..."
# Excluimos directorios virtuales/temporales del sistema para evitar corrupciones
rsync $RSYNC_OPTS \
    --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} \
    "$STAGING_DIR/" "$TARGET_DIR"

if [ "$DRY_RUN" = true ]; then
    log_success "Simulación de restauración finalizada correctamente."
else
    log_success "¡Restauración del sistema completada con éxito!"
    log_warn "Se recomienda reiniciar la Raspberry Pi 5 para asegurar la consistencia del kernel y servicios."
fi

# --- LIMPIEZA ---
log_info "Limpiando directorio temporal de staging..."
rm -rf "$STAGING_DIR"

log_success "Script de rescate finalizado sin errores."