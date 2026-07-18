from app.models.application_profile import ApplicationProfile
from app.services.app_discovery_service import AppDiscoveryService


class ApplicationProfileService:
    """
    Servicio encargado de generar los perfiles de backup de las
    aplicaciones detectadas.

    En esta primera implementación se generan perfiles por defecto.
    Más adelante estos perfiles serán persistentes y editables desde
    la interfaz web.
    """

    def __init__(self):
        self._discovery = AppDiscoveryService()

    def build_profiles(self, applications):
        """
        Genera perfiles a partir de una lista de aplicaciones ya
        descubiertas por DashboardService.
        """

        profiles = []

        for app in applications:

            backup_sources = []

            if isinstance(app, dict):
                mounts = app.get("mounts", [])

                for mount in mounts:
                    source = mount.get("source")
                    if source:
                        backup_sources.append(source)

                name = app.get("name", "unknown")

            else:
                mounts = getattr(app, "mounts", [])

                for mount in mounts:
                    source = getattr(mount, "source", None)
                    if source:
                        backup_sources.append(source)

                name = getattr(app, "name", "unknown")

            profiles.append(
                ApplicationProfile(
                    name=name,
                    application=name,
                    description=f"Perfil generado automáticamente para {name}",
                    enabled=True,
                    backup_sources=sorted(set(backup_sources)),
                    tags=["auto"],
                )
            )

        profiles.sort(key=lambda p: p.name.lower())

        return profiles

    def get_profiles(self):
        """
        Descubre las aplicaciones y genera los perfiles.
        Método de compatibilidad para reutilización interna.
        """

        applications = self._discovery.list_applications()

        return self.build_profiles(applications)

    def get_profile(self, application_name):
        """
        Devuelve el perfil correspondiente a una aplicación o None.
        """

        for profile in self.get_profiles():
            if profile.application == application_name:
                return profile

        return None