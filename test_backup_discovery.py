from app.services.backup_discovery_service import BackupDiscoveryService


service = BackupDiscoveryService()


sources = service.discover_sources()


print()
print("==== BACKUP DISCOVERY ====")
print()


for source in sources:

    print(
        f"""
Aplicación:
{source.application}

Contenedor:
{source.container}

Tipo:
{source.source_type}

Ruta:
{source.path}

Destino:
{source.description}

-------------------------
"""
    )


print(
    f"Total detectados: {len(sources)}"
)
