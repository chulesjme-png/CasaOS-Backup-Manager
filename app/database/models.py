"""
Modelos ORM de SQLAlchemy para la persistencia del gestor de respaldos.
"""

from datetime import datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from app.database.connection import Base


class BackendConfigModel(Base):
    """Configuración guardada para backends de respaldo (ej. Duplicati)."""
    __tablename__ = "backend_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    backend_type = Column(String, nullable=False)
    backend_url = Column(String, nullable=False)
    backend_password = Column(String, default="", nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BackupPlanModel(Base):
    """Plan de respaldo preconfigurado para aplicaciones de CasaOS."""
    __tablename__ = "backup_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    application = Column(String, nullable=False)
    backend_name = Column(String, nullable=False, default="duplicati")
    destination_url = Column(String, nullable=False)
    sources = Column(JSON, nullable=False, default=list)
    excluded_sources = Column(JSON, nullable=False, default=list)
    parameters = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionLogModel(Base):
    """Registro histórico de ejecuciones pasadas."""
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, unique=True, index=True, nullable=False)
    task_id = Column(String, nullable=True)
    application = Column(String, nullable=False)
    backend_name = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    success = Column(Boolean, nullable=False)
    errors = Column(JSON, default=list)
    warnings = Column(JSON, default-list)
    execution_metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)