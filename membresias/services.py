"""
Reglas de negocio de membresías y pagos.

Viven aquí (y no en las vistas) para que cualquier punto de entrada —la API
REST, el admin o un comando— aplique exactamente las mismas reglas.
Lanzan ReglaNegocioError con un mensaje legible cuando algo no se permite.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Membresia, Pago, MAX_DIAS_INICIO_FUTURO


class ReglaNegocioError(Exception):
    """Operación no permitida por las reglas del gimnasio."""


METODOS_CON_COMPROBANTE = ('TRANSFERENCIA', 'DEBITO', 'CREDITO')


def es_admin(usuario):
    return usuario.is_superuser or getattr(usuario, 'rol', None) == 'ADMINISTRADOR'


def validar_socio_sin_membresia_en_curso(socio, excluir_pk=None):
    Membresia.actualizar_vencidas()
    en_curso = Membresia.objects.filter(socio=socio, estado__in=Membresia.ESTADOS_OCUPADOS)
    if excluir_pk:
        en_curso = en_curso.exclude(pk=excluir_pk)
    existente = en_curso.first()
    if existente:
        if existente.estado == 'PENDIENTE':
            detalle = "tiene una membresía pendiente de pago. Registre ese pago o cancélela primero."
        else:
            detalle = (
                f"ya tiene una membresía {existente.get_estado_display().lower()} "
                f"hasta el {existente.fecha_fin:%d/%m/%Y}."
            )
        raise ReglaNegocioError(f"El socio {socio.nombres} {socio.apellidos} {detalle}")


def crear_membresia(socio, plan, usuario, fecha_inicio=None):
    """
    La recepción elige socio, plan y (opcionalmente) la fecha de inicio.
    La fecha de término, el importe y el estado los calcula el sistema.
    """
    hoy = timezone.localdate()
    fecha_inicio = fecha_inicio or hoy
    if fecha_inicio < hoy:
        raise ReglaNegocioError("La fecha de inicio no puede ser anterior a hoy.")
    if fecha_inicio > hoy + timedelta(days=MAX_DIAS_INICIO_FUTURO):
        raise ReglaNegocioError(f"La fecha de inicio puede programarse como máximo {MAX_DIAS_INICIO_FUTURO} días hacia adelante.")

    if not socio.activo:
        raise ReglaNegocioError("No se pueden contratar planes para un socio inactivo.")
    if not plan.activo:
        raise ReglaNegocioError("El plan seleccionado no está disponible para la venta.")

    validar_socio_sin_membresia_en_curso(socio)

    membresia = Membresia(socio=socio, plan=plan, registrado_por=usuario)
    membresia.asignar_fechas_desde(fecha_inicio)
    membresia.importe_acordado = plan.precio
    membresia.estado = 'PENDIENTE'
    membresia.save()
    return membresia


def registrar_pago(membresia_id, usuario, metodo_pago, comprobante_ref=None):
    """
    Registra el ÚNICO pago de una membresía pendiente y la activa.
    - Si la fecha de inicio elegida es futura, se respeta (el socio entra desde ese día).
    - Si ya pasó (se pagó tarde), el inicio se corre al día del pago: el socio
      no pierde días que pagó pero no pudo usar.
    El monto siempre es el importe acordado (nunca lo envía el cliente).
    """
    comprobante_ref = (comprobante_ref or '').strip() or None
    if metodo_pago not in dict(Pago.METODOS):
        raise ReglaNegocioError("Método de pago no válido.")
    if metodo_pago in METODOS_CON_COMPROBANTE and not comprobante_ref:
        raise ReglaNegocioError("Para pagos con transferencia o tarjeta debe ingresar el número de comprobante.")

    with transaction.atomic():
        # Bloqueo de fila: si dos personas cobran a la vez, solo una lo logra.
        membresia = Membresia.objects.select_for_update().select_related('plan').get(pk=membresia_id)
        if membresia.estado != 'PENDIENTE' or membresia.pagos.exists():
            raise ReglaNegocioError(
                f"Esta membresía está '{membresia.get_estado_display()}': "
                "solo se pueden cobrar membresías pendientes de pago."
            )

        pago = Pago.objects.create(
            membresia=membresia,
            usuario_responsable=usuario,
            monto=membresia.importe_acordado,
            metodo_pago=metodo_pago,
            comprobante_ref=comprobante_ref,
        )
        membresia.asignar_fechas_desde(max(membresia.fecha_inicio, timezone.localdate()))
        membresia.estado = 'ACTIVA'
        membresia.save(update_fields=['fecha_inicio', 'fecha_fin', 'estado'])

    return membresia, pago


def cambiar_estado(membresia_id, nuevo_estado, usuario):
    with transaction.atomic():
        membresia = Membresia.objects.select_for_update().get(pk=membresia_id)

        if not membresia.puede_cambiar_a(nuevo_estado):
            raise ReglaNegocioError(
                f"No se puede pasar una membresía '{membresia.get_estado_display()}' a '{nuevo_estado}'."
            )
        # Cancelar una membresía ya pagada = anular una venta: solo administradores.
        if nuevo_estado == 'CANCELADA' and membresia.esta_pagada and not es_admin(usuario):
            raise ReglaNegocioError("Solo un administrador puede cancelar una membresía que ya fue pagada.")

        if nuevo_estado == 'CONGELADA':
            membresia.congelar()
        elif nuevo_estado == 'ACTIVA':
            membresia.descongelar()
        else:
            membresia.estado = 'CANCELADA'
            membresia.fecha_congelamiento = None
        membresia.save()
    return membresia


def eliminar_membresia(membresia):
    """Solo se pueden borrar borradores (pendientes y sin pagos). El resto se cancela."""
    if membresia.estado != 'PENDIENTE' or membresia.pagos.exists():
        raise ReglaNegocioError(
            "Solo se pueden eliminar membresías pendientes de pago. Para las demás use 'Cancelar'."
        )
    membresia.delete()
