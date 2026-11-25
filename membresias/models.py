import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from socios.models import Socio


# Todas las membresías del gimnasio son MENSUALES: 30 días corridos.
DURACION_PLAN_DIAS = 30
# Hasta cuántos días hacia adelante se puede programar el inicio de una membresía.
MAX_DIAS_INICIO_FUTURO = 60


class Plan(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Plan")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    duracion_dias = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Duración (Días)"
    )
    precio = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Precio"
    )
    activo = models.BooleanField(default=True, verbose_name="Disponible para Venta")

    def calcular_fecha_fin(self, fecha_inicio):
        """
        Fecha de término INCLUSIVA: un plan de 30 días que parte el 01/12
        termina el 30/12 (el socio puede entrar ese día completo).
        """
        return fecha_inicio + timedelta(days=self.duracion_dias - 1)

    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.duracion_dias} días)"


class Membresia(models.Model):
    # Ciclo de vida:
    #   PENDIENTE --(pago)--> ACTIVA --(fecha_fin pasa)--> VENCIDA
    #                         ACTIVA <--> CONGELADA (al descongelar se extiende fecha_fin)
    #   PENDIENTE / ACTIVA / CONGELADA --> CANCELADA
    ESTADOS = (
        ('PENDIENTE', 'Pendiente de Pago'),
        ('ACTIVA', 'Activa'),
        ('VENCIDA', 'Vencida'),
        ('CONGELADA', 'Congelada'),
        ('CANCELADA', 'Cancelada'),
    )

    # Estados que "ocupan" al socio: no puede tener otra membresía mientras
    # tenga una en cualquiera de estos estados.
    ESTADOS_OCUPADOS = ('PENDIENTE', 'ACTIVA', 'CONGELADA')

    # Transiciones manuales permitidas desde la interfaz (el paso
    # PENDIENTE -> ACTIVA solo ocurre al registrar el pago, y
    # ACTIVA -> VENCIDA solo lo hace el sistema).
    TRANSICIONES = {
        'PENDIENTE': ('CANCELADA',),
        'ACTIVA': ('CONGELADA', 'CANCELADA'),
        'CONGELADA': ('ACTIVA', 'CANCELADA'),
        'VENCIDA': (),
        'CANCELADA': (),
    }

    socio = models.ForeignKey(Socio, on_delete=models.RESTRICT, related_name='membresias', verbose_name="Socio")
    plan = models.ForeignKey(Plan, on_delete=models.RESTRICT, related_name='membresias', verbose_name="Plan Contratado")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Término")
    importe_acordado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Importe Acordado")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', verbose_name="Estado de Vigencia")
    fecha_congelamiento = models.DateField(
        blank=True, null=True,
        verbose_name="Congelada desde"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name="Registrado por"
    )
    qr_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="Token único del Código QR"
    )
    qr_enviado = models.BooleanField(default=False, verbose_name="QR Enviado por Correo")

    def __str__(self):
        return f"Membresía {self.socio.nombres} {self.socio.apellidos} — {self.estado}"

    # ------------------------------------------------------------------
    # Reglas de negocio (viven en el modelo, no en las vistas, para que
    # cualquier vista, el admin o un futuro API apliquen las mismas reglas)
    # ------------------------------------------------------------------

    def asignar_fechas_desde(self, fecha_inicio):
        """Las fechas SIEMPRE salen del plan; nunca se ingresan a mano."""
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = self.plan.calcular_fecha_fin(fecha_inicio)

    def puede_cambiar_a(self, nuevo_estado):
        return nuevo_estado in self.TRANSICIONES.get(self.estado, ())

    def esta_vigente(self, fecha=None):
        fecha = fecha or timezone.localdate()
        return self.estado == 'ACTIVA' and self.fecha_inicio <= fecha <= self.fecha_fin

    @property
    def esta_pagada(self):
        return self.pagos.exists()

    def congelar(self, fecha=None):
        self.estado = 'CONGELADA'
        self.fecha_congelamiento = fecha or timezone.localdate()

    def descongelar(self, fecha=None):
        """
        Al reactivar, se devuelven al socio los días que estuvo congelada:
        la fecha de término se corre en la misma cantidad de días.
        """
        fecha = fecha or timezone.localdate()
        if self.fecha_congelamiento:
            dias_congelada = (fecha - self.fecha_congelamiento).days
            if dias_congelada > 0:
                self.fecha_fin += timedelta(days=dias_congelada)
        self.fecha_congelamiento = None
        self.estado = 'ACTIVA'

    @classmethod
    def actualizar_vencidas(cls):
        """Marca como VENCIDA toda membresía ACTIVA cuya fecha de término ya pasó."""
        return cls.objects.filter(
            estado='ACTIVA', fecha_fin__lt=timezone.localdate()
        ).update(estado='VENCIDA')


class Pago(models.Model):
    METODOS = (
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('DEBITO', 'Débito'),
        ('CREDITO', 'Crédito'),
    )

    # PROTECT: un pago es un registro contable; nunca debe desaparecer
    # porque alguien borre la membresía asociada.
    membresia = models.ForeignKey(Membresia, on_delete=models.PROTECT, related_name='pagos', verbose_name="Membresía")
    usuario_responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Trabajador Responsable")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Pagado")
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Pago")
    metodo_pago = models.CharField(max_length=30, choices=METODOS, verbose_name="Método de Pago")
    comprobante_ref = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia/Nº Comprobante")

    def __str__(self):
        return f"Pago ${self.monto} - Membresía #{self.membresia.id}"


class IngresoGimnasio(models.Model):
    # NOTA: modelo sin uso (el control de acceso real usa socios.RegistroAcceso).
    # Se mantiene para no romper migraciones existentes.
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='ingresos', verbose_name="Socio")
    usuario_registro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Validado por")
    fecha_hora_entrada = models.DateTimeField(auto_now_add=True, verbose_name="Hora de Entrada")
    fecha_hora_salida = models.DateTimeField(blank=True, null=True, verbose_name="Hora de Salida")

    def __str__(self):
        return f"Ingreso: {self.socio.nombres} - {self.fecha_hora_entrada.strftime('%Y-%m-%d %H:%M')}"
