from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def redirigir_seguro(request, url_por_defecto, *args, **kwargs):
    """
    Vuelve a la página desde donde se hizo la acción, pero SOLO si esa URL
    pertenece a este mismo sitio. Evita "open redirects": que un enlace
    malicioso mande al usuario a otro dominio usando nuestra app.

    Prioridad: campo oculto `next` del formulario > cabecera Referer > url_por_defecto.
    """
    candidata = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if candidata and url_has_allowed_host_and_scheme(
        candidata,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(candidata)
    return redirect(url_por_defecto, *args, **kwargs)
