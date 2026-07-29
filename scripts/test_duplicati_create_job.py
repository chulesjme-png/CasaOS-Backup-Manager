from app.connectors.duplicati.duplicati_client import DuplicatiClient
import json


client = DuplicatiClient(
    base_url="http://192.168.1.10:8200",
    password="MiContraseñaSegura2026",
)


payload = {

    "Backup": {

        "ID": None,

        "Name": "CasaOS-Test",

        "Description": (
            "Prueba CasaOS Backup Manager"
        ),

        "Tags": [],

        "TargetURL": (
            "file:///tmp/duplicati-test"
        ),

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

    client.authenticate()

    result = client.create_job(
        payload
    )

    print(
        "\n===== RESULT ====="
    )

    print(
        json.dumps(
            result,
            indent=4,
            default=str,
        )
    )

except Exception as exc:

    print(
        "\n===== ERROR ====="
    )

    print(exc)