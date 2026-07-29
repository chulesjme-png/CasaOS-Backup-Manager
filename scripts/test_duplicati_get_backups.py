from app.connectors.duplicati.duplicati_client import DuplicatiClient
import json


client = DuplicatiClient(
    base_url="http://192.168.1.10:8200",
    password="MiContraseñaSegura2026",
)


client.authenticate()


backups = client.get_backups()


print("\n===== DUPLICATI BACKUPS =====")


print(
    json.dumps(
        backups,
        indent=4,
        default=str,
    )
)


print("============================")