from __future__ import annotations

import shutil


class DiskService:
    """Información del disco principal."""

    @staticmethod
    def get_usage(path: str = "/") -> dict:

        total, used, free = shutil.disk_usage(path)

        percent = round((used / total) * 100, 1)

        return {

            "total_gb": round(total / 1024**3, 1),

            "used_gb": round(used / 1024**3, 1),

            "free_gb": round(free / 1024**3, 1),

            "percent": percent,
        }