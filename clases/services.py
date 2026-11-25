"""Reglas de negocio de sesiones de clase e inscripciones (cupos y lista de espera)."""
from django.db import transaction
from django.utils import timezone

from membresias.services import ReglaNegocioError
from .models import SesionClase, InscripcionClase


def validar_horario_sesion(*, fecha, hora_inicio, hora_fin, sala, entrenador, cupo_maximo, instancia=None):
    """Devuelve un dict {campo: mensaje} con los errores encontrados (vacío si todo está bien)."""
    errores = {}

    if hora_inicio and hora_fin and hora_fin <= hora_inicio:
        errores['hora_fin'] = "La hora de término debe ser posterior a la hora de inicio."

    if cupo_maximo is not None and cupo_maximo < 1:
        errores['cupo_maximo'] = "El cupo debe ser al menos 1."
    elif sala and cupo_maximo and cupo_maximo > sala.capacidad_maxima:
        errores['cupo_maximo'] = (
            f"El cupo ({cupo_maximo}) supera la capacidad de {sala.nombre} ({sala.capacidad_maxima} personas)."
        )

    if fecha and instancia is None and fecha < timezone.localdate():
        errores['fecha'] = "No se pueden programar sesiones en una fecha pasada."

    if fecha and hora_inicio and hora_fin and hora_fin > hora_inicio:
        traslapes = SesionClase.objects.filter(
            fecha=fecha, hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio
        ).exclude(estado='CANCELADA')
        if instancia is not None:
            traslapes = traslapes.exclude(pk=instancia.pk)
        if sala and traslapes.filter(sala=sala).exists():
            errores['sala'] = f"{sala.nombre} ya está reservada en ese horario."
        if entrenador and traslapes.filter(entrenador=entrenador).exists():
            errores['entrenador'] = (
                f"{entrenador.first_name} {entrenador.last_name} ya dicta otra clase en ese horario."
            )
    return errores


def inscribir_socio(sesion_id, socio, usuario):
    """Inscribe con cupo confirmado o, si está llena, en lista de espera."""
    with transaction.atomic():
        sesion = SesionClase.objects.select_for_update().get(pk=sesion_id)

        if sesion.estado != 'PROGRAMADA' or sesion.fecha < timezone.localdate():
            raise ReglaNegocioError("Solo se puede inscribir en sesiones programadas que aún no han pasado.")
        if not socio.activo:
            raise ReglaNegocioError("El socio está inactivo.")
        if not socio.membresias.filter(
            estado='ACTIVA', fecha_inicio__lte=sesion.fecha, fecha_fin__gte=sesion.fecha
        ).exists():
            raise ReglaNegocioError(
                f"{socio.nombres} no tiene una membresía activa vigente para el día de la clase."
            )
        if InscripcionClase.objects.filter(socio=socio, sesion=sesion).exists():
            raise ReglaNegocioError(f"{socio.nombres} ya está inscrito o en lista de espera de esta clase.")

        confirmados = sesion.inscritos.filter(en_espera=False).count()
        hay_cupo = confirmados < sesion.cupo_maximo
        inscripcion = InscripcionClase.objects.create(
            socio=socio, sesion=sesion, registrado_por=usuario, en_espera=not hay_cupo
        )
    return inscripcion


def cancelar_inscripcion(inscripcion_id):
    """Elimina la inscripción y, si liberaba un cupo, promueve al primero en espera."""
    with transaction.atomic():
        inscripcion = InscripcionClase.objects.select_for_update().select_related('socio').get(pk=inscripcion_id)
        sesion_id = inscripcion.sesion_id
        liberaba_cupo = not inscripcion.en_espera
        inscripcion.delete()

        promovido = None
        if liberaba_cupo:
            promovido = InscripcionClase.objects.select_for_update().filter(
                sesion_id=sesion_id, en_espera=True
            ).order_by('fecha_inscripcion').first()
            if promovido:
                promovido.en_espera = False
                promovido.save(update_fields=['en_espera'])
    return promovido
