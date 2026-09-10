from pydantic import BaseModel, Field
from typing import Optional

class RestoreRequest(BaseModel):
    snapshot_id: Optional[str] = Field(None, description="Identificador del punto de restauración")
    backup_id: Optional[str] = Field(None, description="ID alternativo de la copia")
    backup_file: Optional[str] = Field(None, description="Ruta o nombre del archivo comprimido")
    target_app: Optional[str] = Field(None, description="Nombre del contenedor/aplicación destino")
    target_path: str = Field("/DATA/AppData", description="Ruta absoluta base de los datos de la aplicación")
    engine: str = Field("auto", description="Motor de extracción ('auto', 'tar', 'borg')")
    overwrite: bool = Field(True, description="Realizar copia preventina .bak y sobrescribir el directorio")
    dry_run: bool = Field(False, description="Simular la extracción sin alterar los archivos de producción")

class RestoreResponse(BaseModel):
    status: str
    task_id: str
    message: str
    resolved_path: str