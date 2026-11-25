from rest_framework.permissions import BasePermission

ADMIN = 'ADMINISTRADOR'
RECEPCION = 'RECEPCIONISTA'
ENTRENADOR = 'ENTRENADOR'
STAFF = (ADMIN, RECEPCION)
TODOS = (ADMIN, RECEPCION, ENTRENADOR)


def tiene_rol(usuario, roles):
    return bool(
        usuario and usuario.is_authenticated and usuario.is_active
        and (usuario.is_superuser or getattr(usuario, 'rol', None) in roles)
    )


class PorRol(BasePermission):
    """
    Autorización por rol. Cada vista declara:
        roles = (...)                      -> roles permitidos por defecto
        roles_por_accion = {'destroy': (ADMIN,), ...}  -> excepciones por acción
    Autenticación (¿quién eres?) la resuelve JWT; esto es AUTORIZACIÓN (¿qué puedes hacer?).
    """
    message = "No tienes permisos para realizar esta acción."

    def has_permission(self, request, view):
        accion = getattr(view, 'action', None)
        roles = getattr(view, 'roles_por_accion', {}).get(accion) or getattr(view, 'roles', TODOS)
        return tiene_rol(request.user, roles)
