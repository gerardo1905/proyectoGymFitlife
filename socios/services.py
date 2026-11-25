"""Reglas de negocio del control de acceso al gimnasio (torniquete / recepción)."""
import uuid

from django.core.exceptions import ValidationError
from django.utils import timezone

from fitlife_config.validators import sanitizar_y_validar_rut
from membresias.models import Membresia
from .models import Socio, RegistroAcceso


def _rechazo(usuario, socio, motivo_corto, motivo_largo):
    if socio:
        RegistroAcceso.objects.create(
            socio=socio, permitido=False, motivo_rechazo=motivo_corto, registrado_por=usuario
        )
    return {'permitido': False, 'motivo': motivo_largo, 'socio': socio, 'membresia': None, 'dias_restantes': None}


def validar_ingreso(dato_escaneado, usuario):
    """
    Decide si un socio puede entrar. Acepta el token UUID del QR (normal) o un
    RUT tipeado (respaldo si el socio no trae su QR). Siempre deja registro.
    """
    dato_escaneado = (dato_escaneado or '').strip()
    hoy = timezone.localdate()
    Membresia.actualizar_vencidas()

    socio = None
    membresia_del_qr = None

    try:
        token_qr = uuid.UUID(dato_escaneado)
    except (ValueError, AttributeError, TypeError):
        token_qr = None

    if token_qr:
        membresia_del_qr = Membresia.objects.select_related('socio').filter(qr_token=token_qr).first()
        if not membresia_del_qr:
            return _rechazo(usuario, None, '', "El código QR escaneado no corresponde a ninguna membresía.")
        socio = membresia_del_qr.socio
    else:
        try:
            socio = Socio.objects.filter(rut=sanitizar_y_validar_rut(dato_escaneado)).first()
        except ValidationError:
            socio = None
        if not socio:
            return _rechazo(usuario, None, '', f"'{dato_escaneado}' no corresponde a ningún socio registrado.")

    nombre = f"{socio.nombres} {socio.apellidos}"

    if not socio.activo:
        return _rechazo(usuario, socio, "Cuenta de Socio Inactiva", f"Socio {nombre} se encuentra INACTIVO.")

    # Membresía pagada que todavía no comienza (inicio programado a futuro).
    futura = membresia_del_qr if membresia_del_qr and membresia_del_qr.estado == 'ACTIVA' else None
    if futura is None and not membresia_del_qr:
        futura = Membresia.objects.filter(socio=socio, estado='ACTIVA', fecha_inicio__gt=hoy).first()
    if futura and futura.fecha_inicio > hoy and not Membresia.objects.filter(
        socio=socio, estado='ACTIVA', fecha_inicio__lte=hoy, fecha_fin__gte=hoy
    ).exists():
        return _rechazo(usuario, socio, "Membresía aún no comienza",
                        f"La membresía de {nombre} comienza el {futura.fecha_inicio:%d/%m/%Y}.")

    # Un QR viejo no sirve aunque el socio tenga otra membresía vigente.
    if membresia_del_qr and not membresia_del_qr.esta_vigente(hoy):
        return _rechazo(
            usuario, socio, "QR de membresía no vigente",
            f"El QR de {nombre} pertenece a una membresía {membresia_del_qr.get_estado_display().upper()}. "
            "Debe usar el QR de su membresía actual."
        )

    membresia_vigente = membresia_del_qr or Membresia.objects.filter(
        socio=socio, estado='ACTIVA', fecha_inicio__lte=hoy, fecha_fin__gte=hoy
    ).first()
    if not membresia_vigente:
        return _rechazo(usuario, socio, "Membresía Vencida o Inexistente",
                        f"Socio {nombre} no cuenta con una membresía ACTIVA vigente.")

    # Evita doble ingreso (QR compartido) e inflar el aforo.
    if RegistroAcceso.objects.filter(socio=socio, permitido=True, fecha_hora_salida__isnull=True).exists():
        return _rechazo(usuario, socio, "Ingreso duplicado",
                        f"{nombre} ya figura DENTRO del gimnasio. Registre su salida antes de un nuevo ingreso.")

    RegistroAcceso.objects.create(socio=socio, permitido=True, registrado_por=usuario)
    return {
        'permitido': True,
        'motivo': '',
        'socio': socio,
        'membresia': membresia_vigente,
        'dias_restantes': (membresia_vigente.fecha_fin - hoy).days,
    }
