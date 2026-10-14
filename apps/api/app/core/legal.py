"""Documentos legales y retención de datos (feature 028, Ley 1581 de 2012).

Publicar una versión nueva de los Términos o la Política de privacidad = cambiar
`LEGAL_VERSION` (y la fecha visible en /terms y /privacy de la web) en un PR: todos los
usuarios deben aceptarla de nuevo antes de seguir usando la app.
"""

from __future__ import annotations

LEGAL_VERSION = "2026-10-14"

#: Días que se conserva el nombre del huésped después de la fecha de salida.
GUEST_NAME_RETENTION_DAYS = 365

#: Rutas con sesión que responden aunque falte aceptar la versión vigente.
TERMS_EXEMPT_PATHS = frozenset(
    {"/auth/me", "/auth/terms/accept", "/auth/logout", "/auth/logout-all"}
)
