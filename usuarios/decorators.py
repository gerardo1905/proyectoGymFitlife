from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def rol_requerido(*roles_permitidos):
    """
    Decorador personalizado para verificar si el usuario autenticado
    posee uno de los roles autorizados para acceder a la vista.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # El superusuario (is_superuser) siempre tiene acceso total
            if request.user.is_superuser or request.user.rol in roles_permitidos:
                return view_func(request, *args, **kwargs)

            messages.error(request, "Acceso denegado: No tienes los permisos necesarios para realizar esta acción.")
            return redirect('home')
        return _wrapped_view
    return decorator