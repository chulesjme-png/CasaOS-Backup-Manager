from app.models.application_profile import ApplicationProfile
from app.services.app_discovery_service import AppDiscoveryService
from app.services.storage_resolver_service import StorageResolverService


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
        self._storage_resolver = StorageResolverService()

    def build_profiles(self, applications):
        """
        Genera perfiles a partir de una lista de aplicaciones ya
        descubiertas por DashboardService.
        """

        profiles = []

        for app in applications:

            name = app.get("name", "unknown")

            resources = self._storage_resolver.resolve(app)

            profiles.append(
                ApplicationProfile(
                    name=name,
                    application=name,
                    description=f"Perfil generado automáticamente para {name}",
                    enabled=True,
                    resources=resources,
                    tags=["auto"],
                )
            )

        profiles.sort(
            key=lambda profile: profile.name.lower()
        )

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