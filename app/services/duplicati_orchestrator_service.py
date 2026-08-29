import urllib.parse
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DuplicatiOrchestratorService:
    def __init__(self, duplicati_backend):
        """
        Inyecta el adaptador de infraestructura que se comunica directamente 
        con la API REST de Duplicati (puerto 8200).
        """
        self.duplicati = duplicati_backend

    def _sanitize_target_url(self, raw_path: str) -> str:
        """
        Fuerza la codificación estricta de la URI para evitar HTTP 400 Bad Request
        en el backend de C# de Duplicati.
        Mantiene los separadores de ruta ('/') intactos pero codifica espacios, 
        corchetes y otros caracteres especiales (ej. %5BCBM%5D%20Sistema_Completo).
        """
        # Limpiamos el prefijo file:// si el orquestador o la BD ya lo incluyó por error humano
        clean_path = raw_path.replace("file://", "")
        
        # Sanitización estricta respetando los slashes de los directorios
        sanitized_path = urllib.parse.quote(clean_path, safe='/')
        
        # Garantizar que la ruta comience con '/' antes de aplicar el prefijo de protocolo
        if not sanitized_path.startswith('/'):
            sanitized_path = f"/{sanitized_path}"
            
        return f"file://{sanitized_path}"

    def _build_task_payload(self, task_name: str, source_paths: List[str], destination_path: str) -> Dict[str, Any]:
        """
        Construye el contrato JSON estricto esperado por Duplicati para la autocreación.
        """
        target_url = self._sanitize_target_url(destination_path)
        
        return {
            "Schedule": None,
            "Backup": {
                "Name": task_name,
                "Description": "Backup autogestionado por CasaOS Backup Manager",
                "Tags": ["CasaOS", "CBM-Auto"],
                "TargetURL": target_url,
                "DBPath": "", 
            },
            "Filters": [],
            "Options": [
                {
                    "Name": "no-encryption",
                    "Value": "true"
                }
            ],
            "Sources": source_paths
        }

    async def _get_task_id_by_name(self, task_name: str) -> Optional[str]:
        """
        Consulta la API de Duplicati para buscar si la tarea ya existe y recupera su ID.
        """
        tasks_response = await self.duplicati.get_all_tasks()
        
        # Duplicati devuelve una lista de diccionarios, iteramos para validar existencia
        for task in tasks_response:
            backup_data = task.get("Backup", {})
            if backup_data.get("Name") == task_name:
                return str(task.get("Id"))
                
        return None

    async def run_system_backup(self, task_name: str, source_paths: List[str], destination_path: str) -> Dict[str, Any]:
        """
        Orquesta la ejecución de "Sistema Completo".
        Si la tarea no existe (primer clic del usuario), la autoconfigura en Duplicati 
        antes de desencadenar la ejecución.
        """
        logger.info(f"[CBM-Duplicati] Solicitud de backup recibida: {task_name}")
        
        task_id = await self._get_task_id_by_name(task_name)
        
        if not task_id:
            logger.info(f"[CBM-Duplicati] La tarea '{task_name}' no existe. Autocreando...")
            payload = self._build_task_payload(task_name, source_paths, destination_path)
            
            creation_response = await self.duplicati.create_task(payload)
            
            if "Id" not in creation_response:
                logger.error(f"[CBM-Duplicati] Fallo crítico al crear tarea. Payload: {payload} | Respuesta: {creation_response}")
                raise ValueError("La API de Duplicati rechazó la creación de la tarea. Verifique los logs del backend.")
                
            task_id = str(creation_response["Id"])
            logger.info(f"[CBM-Duplicati] Tarea creada exitosamente con ID: {task_id}")

        logger.info(f"[CBM-Duplicati] Lanzando ejecución para tarea ID: {task_id}")
        execution_response = await self.duplicati.run_task(task_id)
        
        return {
            "status": "success",
            "message": "Backup encolado correctamente en el motor de Duplicati.",
            "task_id": task_id,
            "engine_response": execution_response
        }