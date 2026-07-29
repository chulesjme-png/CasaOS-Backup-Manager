from uuid import uuid4
import json

from app.connectors.duplicati.duplicati_client import DuplicatiClient


client = DuplicatiClient(
    base_url="http://192.168.1.10:8200",
    password="MiContraseñaSegura2026",
)

backup_name = f"CasaOS-Test-{uuid4().hex[:8]}"

payload = {
    "Backup": {
        "ID": None,
        "Name": backup_name,
        "Description": "Prueba CasaOS Backup Manager",
        "Tags": [],
        "TargetURL": "file:///tmp/duplicati-test",
        "Sources": [
            "/tmp/test"
        ],
        "Settings": [
            {
                "Name": "encryption-module",
                "Value": "aes",
            },
            {
                "Name": "passphrase",
                "Value": "test-password",
            },
        ],
        "Filters": [],
    }
}

try:
    print(f"\n===== CREATING BACKUP: {backup_name} =====")

    client.authenticate()

    result = client.create_job(payload)

    print("\n===== RESULT =====")

    print(
        json.dumps(
            result,
            indent=4,
            default=str,
        )
    )

except Exception as exc:

    print("\n===== ERROR =====")
    print(exc)