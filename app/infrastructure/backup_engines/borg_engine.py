import asyncio
import json
import os
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional


class BorgEngineError(Exception):
    """Excepción para errores generados por el motor de BorgBackup."""
    pass


class BorgEngine:
    """
    Motor de respaldo basado en BorgBackup CLI.
    Proporciona deduplicación a nivel de bloques, compresión zstd y emite
    progreso estructurado en formato JSON para el consumo en tiempo real.
    """

    def __init__(self, borg_binary: str = "borg"):
        self.borg_binary = borg_binary

    async def init_repository(
        self, 
        repo_path: str, 
        encryption: str = "none"
    ) -> Dict[str, Any]:
        """
        Inicializa un repositorio de BorgBackup en la ruta especificada.
        """
        cmd = [
            self.borg_binary,
            "init",
            f"--encryption={encryption}",
            repo_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise BorgEngineError(
                f"Error al inicializar el repositorio Borg: {stderr.decode().strip()}"
            )

        return {"status": "success", "repo_path": repo_path}

    async def create_backup(
        self,
        repo_path: str,
        archive_name: str,
        sources: List[str],
        compression: str = "zstd,3",
        passphrase: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Crea un nuevo archivo de respaldo dentro del repositorio Borg.
        Transmite eventos de progreso en JSON si se provee un callback.
        """
        archive_target = f"{repo_path}::{archive_name}"
        cmd = [
            self.borg_binary,
            "create",
            "--json",
            "--progress",
            f"--compression={compression}",
            "--exclude", "*/data/*.log",
            "--exclude", "*/cache/*",
            archive_target,
        ] + sources

        env = os.environ.copy()
        if passphrase:
            env["BORG_PASSPHRASE"] = passphrase

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        if process.stderr:
            async for line in self._read_stream(process.stderr):
                event = self._parse_json_line(line)
                if event and progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(event)
                    else:
                        progress_callback(event)

        stdout, stderr = await process.communicate()

        # Borg retorna 1 para advertencias menores (archivos modificados en caliente).
        # Solo se lanza excepción si el código de retorno es mayor a 1 (error fatal).
        if process.returncode > 1:
            raise BorgEngineError(
                f"Error durante la creación del backup Borg: {stderr.decode().strip()}"
            )

        summary = self._parse_json_line(stdout.decode("utf-8")) or {}
        return {
            "status": "completed",
            "archive": archive_name,
            "summary": summary
        }

    async def _read_stream(
        self, 
        stream: asyncio.StreamReader
    ) -> AsyncGenerator[str, None]:
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8")

    @staticmethod
    def _parse_json_line(line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None