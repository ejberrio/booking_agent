"""Errores tipados del conector. Nunca incluyen secretos en su mensaje."""


class ChannelError(Exception):
    """Error genérico de comunicación/operación con el Channel Manager."""


class AuthError(ChannelError):
    """Credenciales inválidas, ausentes o sin permisos."""


class RateLimited(ChannelError):
    """Límite de tasa del proveedor alcanzado tras agotar reintentos."""


class WriteUnverified(ChannelError):
    """La escritura se envió pero no pudo verificarse al releer."""
