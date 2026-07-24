"""
Excepciones comunes para los conectores externos.

Los conectores encapsulan la comunicación con servicios externos
(APIs HTTP, almacenamiento remoto, etc.).

El objetivo de estas excepciones es evitar propagar excepciones
específicas de librerías externas (por ejemplo, requests) hacia
el dominio de la aplicación.
"""


class ConnectorError(Exception):
    """
    Excepción base para cualquier error producido por un conector externo.
    """

    pass


class ConnectorConnectionError(ConnectorError):
    """
    Error al establecer comunicación con el servicio externo.
    """

    pass


class ConnectorAuthenticationError(ConnectorError):
    """
    Error de autenticación contra el servicio externo.
    """

    pass


class ConnectorTimeoutError(ConnectorError):
    """
    Tiempo de espera agotado durante una operación.
    """

    pass


class ConnectorResponseError(ConnectorError):
    """
    El servicio respondió, pero la respuesta no es válida
    o contiene un error.
    """

    pass


class DuplicatiConnectionError(ConnectorConnectionError):
    """
    Error específico de comunicación con el servidor Duplicati.
    """

    pass


class DuplicatiApiError(ConnectorResponseError):
    """
    Error devuelto por la API de Duplicati.
    """

    pass