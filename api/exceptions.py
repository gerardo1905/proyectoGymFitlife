from django.db.models import ProtectedError, RestrictedError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from membresias.services import ReglaNegocioError


def manejador_excepciones(exc, context):
    """
    Convierte errores de negocio y de integridad en respuestas JSON con el
    código HTTP correcto, en vez de un error 500 genérico.
    """
    if isinstance(exc, ReglaNegocioError):
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, (ProtectedError, RestrictedError)):
        return Response(
            {'detail': "No se puede eliminar: el registro tiene información asociada. "
                       "Desactívelo en lugar de eliminarlo."},
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, IntegrityError):
        return Response({'detail': "El registro entra en conflicto con datos existentes."},
                        status=status.HTTP_409_CONFLICT)

    return exception_handler(exc, context)
