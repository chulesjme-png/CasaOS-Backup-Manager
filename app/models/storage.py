from dataclasses import dataclass


@dataclass
class StorageDevice:
    """
    Representa un destino de almacenamiento.

    Puede ser:
    - Sistema
    - USB
    - Local
    - NAS
    """


    name: str

    device: str

    model: str

    serial: str

    transport: str

    mount_point: str

    filesystem: str


    total: int

    used: int

    free: int

    percent: float


    device_type: str


    removable: bool


    available: bool


    backup_supported: bool


    status: str


    description: str