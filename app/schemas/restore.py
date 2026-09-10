from pydantic import BaseModel, Field
from typing import Optional

class RestoreRequest(BaseModel):
    snapshot_id: Optional[str] = Field(None, description="Identificador o nombre de la copia de seguridad")
    backup_id: Optional[str] = Field(None, description="Alias para snapshot_id")
    backup_file: Optional[str] = Field(None, description="Ruta o nombre de archivo del respaldo")
    target_app: Optional[str] = Field(None, description="Nombre de la aplicación de CasaOS (ej. netdata)")
    target_path: str = Field("/DATA/AppData", description="Ruta base de almacenamiento de aplicaciones")
    engine: str = Field("borg", description="Motor de respaldo: 'borg' o 'tar'")
    overwrite: bool = Field(True, description="Sobrescribir datos tras backup preventivo .bak")
    dry_run: bool = Field(False, description="Simular el proceso sin reemplazar la aplicación activa")

class RestoreResponse(BaseModel):
    status: str
    job_id: str
    message: str
    resolved_path: str
    staging_path: str