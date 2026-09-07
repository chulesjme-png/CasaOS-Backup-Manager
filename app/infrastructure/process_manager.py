import asyncio
import logging
import os
import shutil
from typing import Any, Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Gestor de ejecución y limpieza garantizada para tareas de backup.
    Captura interrupciones, ejecuta callbacks de estado (cancel/error)
    y asegura el borrado de directorios/archivos temporales en cualquier escenario.
    """

    def __init__(self):
        self._is_cancelled: bool = False

    async def run_with_cleanup(
        self,
        coro_or_func: Callable[[], Awaitable[Any]],
        cleanup_paths: Optional[List[str]] = None,
        on_cancel: Optional[Callable[[], Awaitable[None] | None]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None] | None]] = None,
    ) -> Any:
        """
        Ejecuta la tarea encapsulada garantizando la eliminación de rutas temporales
        al finalizar, incluso tras excepciones o cancelaciones explícitas.
        """
        cleanup_paths = cleanup_paths or []
        self._is_cancelled = False

        try:
            return await coro_or_func()
        except asyncio.CancelledError:
            self._is_cancelled = True
            logger.warning("Proceso cancelado por intervención del usuario o señal SIGTERM.")
            if on_cancel:
                if asyncio.iscoroutinefunction(on_cancel):
                    await on_cancel()
                else:
                    on_cancel()
            raise
        except Exception as exc:
            logger.error(f"Fallo durante la ejecución del proceso: {exc}")
            if on_error:
                if asyncio.iscoroutinefunction(on_error):
                    await on_error(exc)
                else:
                    on_error(exc)
            raise
        finally:
            self._cleanup_artifacts(cleanup_paths)

    def _cleanup_artifacts(self, paths: List[str]) -> None:
        """
        Elimina artefactos temporales del disco.
        """
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    logger.info(f"Directorio temporal limpiado correctamente: {path}")
                elif os.path.isfile(path):
                    os.remove(path)
                    logger.info(f"Archivo temporal limpiado correctamente: {path}")
            except Exception as e:
                logger.error(f"No se pudo eliminar el artefacto temporal {path}: {e}")