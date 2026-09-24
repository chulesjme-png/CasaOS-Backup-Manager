#!/bin/bash
echo "=========================================="
echo "   RESCATE DEL SISTEMA CASAOS (BORG)      "
echo "=========================================="

# Auto-detecta la ruta absoluta de la carpeta donde se encuentra este script
SCRIPT_DIR="\(( cd "\)( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_PATH="$SCRIPT_DIR/BorgRepo"

export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
export BORG_RELOCATED_REPO_ACCESS_IS_OK=yes

echo "-> Buscando repositorio en: $REPO_PATH"
if [ ! -d "$REPO_PATH" ]; then
    echo "[ERROR] No se encuentra la carpeta 'BorgRepo' en $SCRIPT_DIR."
    echo "Asegúrate de que este script está en la misma carpeta que 'BorgRepo'."
    exit 1
fi

echo "-> Repositorio localizado correctamente."
echo ""
echo "-> Lista de copias de seguridad disponibles:"
echo "------------------------------------------"
borg list "$REPO_PATH"
echo "------------------------------------------"

read -p "Introduce el nombre exacto de la copia a restaurar: " ARCHIVE_NAME

if [ -z "$ARCHIVE_NAME" ]; then
    echo "Nombre vacío. Operación cancelada."
    exit 1
fi

read -s -p "Introduce la contraseña del repositorio (pulsa Enter si no tiene): " BORG_PASSPHRASE
echo ""
export BORG_PASSPHRASE

echo ""
echo "=========================================================="
echo " ¡ATENCIÓN! LEA ATENTAMENTE ANTES DE CONTINUAR            "
echo "=========================================================="
echo "1. Este proceso sobreescribirá los archivos del sistema."
echo "2. Para restaurar todo CasaOS, DEBES estar en la raíz ( cd / )."
echo "3. Directorio actual de ejecución: $(pwd)"
echo "----------------------------------------------------------"
read -p "¿Deseas iniciar la RESTAURACIÓN REAL del sistema? (escribe 'SI' para confirmar): " CONFIRM

if [ "$CONFIRM" = "SI" ]; then
    echo ""
    echo "Iniciando extracción de archivos de $ARCHIVE_NAME..."
    
    # Realiza la extracción real en la ubicación actual
    borg extract --list "\(REPO_PATH::\)ARCHIVE_NAME"
    
    if [ $? -eq 0 ]; then
        echo "=========================================="
        echo " ¡RESTAURACIÓN COMPLETADA CON ÉXITO!      "
        echo " Ejecuta 'sudo reboot' para reiniciar.    "
        echo "=========================================="
    else
        echo "[ERROR] Ocurrieron errores durante la extracción."
    fi
else
    echo "Operación cancelada. No se ha modificado ningún archivo."
fi