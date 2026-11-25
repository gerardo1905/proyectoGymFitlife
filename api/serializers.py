import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from datetime import datetime, timedelta

from clases.models import (TipoClase, Sala, SesionClase, InscripcionClase,
                           DURACION_CLASE_MINUTOS, PRIMERA_HORA_INICIO, ULTIMA_HORA_INICIO)
from clases.services import validar_horario_sesion
from entrenadores.models import AsignacionEntrenador
from equipamiento.models import Equipo, Mantenimiento
from fitlife_config.validators import validador_telefono, sanitizar_y_validar_rut, sanitizar_telefono
from gastos.models import CategoriaGasto, Gasto
from membresias.models import Plan, Membresia, Pago, DURACION_PLAN_DIAS
from socios.models import Socio, RegistroAcceso

Usuario = get_user_model()


def _rut_normalizado(valor):
    try:
        return sanitizar_y_validar_rut(valor)
    except DjangoValidationError as error:
        raise serializers.ValidationError(error.messages)


SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]+$")
TELEFONO_CHILE = re.compile(r"^(\+?56)?\d{9}$")


def _texto_nombre(valor, campo):
    """Limpia espacios, valida que sean solo letras y deja Mayúscula Inicial."""
    limpio = ' '.join((valor or '').split())
    if not limpio:
        raise serializers.ValidationError(f"Ingrese {campo}.")
    if not SOLO_LETRAS.match(limpio):
        raise serializers.ValidationError(f"{campo.capitalize()} solo puede contener letras.")
    return limpio.title()


def _telefono_chileno(valor):
    """Acepta 9XXXXXXXX, 56 9XXXXXXXX o +56 9XXXXXXXX (con o sin espacios) y lo guarda como +569XXXXXXXX."""
    digitos = sanitizar_telefono(valor or '')
    if not TELEFONO_CHILE.match(digitos):
        raise serializers.ValidationError("Ingrese un teléfono chileno de 9 dígitos (ej: 9 1234 5678).")
    nueve = digitos[-9:]
    return f"+56{nueve}"


def _nombre(persona):
    if persona is None:
        return None
    return f"{persona.first_name} {persona.last_name}".strip() or persona.username


# ======================= AUTENTICACIÓN (JWT) =======================

class UsuarioResumenSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'rol', 'rol_display',
                  'is_superuser', 'telefono', 'especialidad']
        read_only_fields = fields


class LoginSerializer(TokenObtainPairSerializer):
    """Devuelve access + refresh y los datos básicos del usuario (sin datos sensibles)."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = user.rol
        token['nombre'] = _nombre(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['usuario'] = UsuarioResumenSerializer(self.user).data
        return data


class PerfilSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                     validators=[validador_telefono])

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'rut', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'rol_display', 'especialidad']
        read_only_fields = ['id', 'username', 'rut', 'rol', 'especialidad']

    def validate_telefono(self, valor):
        return _telefono_chileno(valor) if valor else None

    def validate_email(self, valor):
        return (valor or '').strip().lower()

    def validate_first_name(self, valor):
        return _texto_nombre(valor, 'los nombres')

    def validate_last_name(self, valor):
        return _texto_nombre(valor, 'los apellidos')


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True)

    def validate_password_actual(self, valor):
        if not self.context['request'].user.check_password(valor):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return valor

    def validate_password_nueva(self, valor):
        validate_password(valor, self.context['request'].user)
        return valor


# ======================= TRABAJADORES =======================

class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                     validators=[validador_telefono])
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'rut', 'first_name', 'last_name', 'email', 'rol', 'rol_display',
                  'telefono', 'especialidad', 'is_active', 'date_joined', 'password']
        read_only_fields = ['id', 'date_joined']

    def validate_rut(self, valor):
        rut = _rut_normalizado(valor)
        qs = Usuario.objects.filter(rut=rut)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un trabajador con este RUT.")
        return rut

    def validate_telefono(self, valor):
        return _telefono_chileno(valor) if valor else None

    def validate_email(self, valor):
        return (valor or '').strip().lower()  # el modelo de usuario guarda '' (no NULL) cuando no hay correo

    def validate_first_name(self, valor):
        return _texto_nombre(valor, 'los nombres')

    def validate_last_name(self, valor):
        return _texto_nombre(valor, 'los apellidos')

    def validate_username(self, valor):
        valor = valor.strip().lower()
        if not re.match(r'^[a-z0-9._-]{3,30}$', valor):
            raise serializers.ValidationError("Use de 3 a 30 caracteres: letras minúsculas, números, punto, guion.")
        return valor

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': "La contraseña es obligatoria."})
        if self.instance is not None:
            # El RUT y el usuario identifican al trabajador: no se cambian después.
            attrs.pop('rut', None)
            attrs.pop('username', None)
            attrs.pop('password', None)  # se cambia con la acción /cambiar-password/
        if attrs.get('password'):
            candidato = Usuario(username=attrs.get('username'), email=attrs.get('email'),
                                first_name=attrs.get('first_name', ''), last_name=attrs.get('last_name', ''))
            try:
                validate_password(attrs['password'], candidato)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'password': error.messages})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)  # se guarda con hash (PBKDF2), nunca en texto plano
        usuario.save()
        return usuario


class PasswordAdminSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, valor):
        validate_password(valor, self.context.get('trabajador'))
        return valor


# ======================= SOCIOS Y ACCESO =======================

class SocioSerializer(serializers.ModelSerializer):
    telefono = serializers.CharField(validators=[validador_telefono])
    membresia_vigente = serializers.SerializerMethodField()

    class Meta:
        model = Socio
        fields = ['id', 'rut', 'nombres', 'apellidos', 'email', 'telefono', 'contacto_emergencia',
                  'fecha_registro', 'activo', 'membresia_vigente']
        read_only_fields = ['id', 'fecha_registro']

    def get_membresia_vigente(self, socio):
        hoy = timezone.localdate()
        for m in socio.membresias.all():  # usa prefetch_related de la vista
            if m.estado in ('ACTIVA', 'CONGELADA', 'PENDIENTE') and m.fecha_fin >= hoy:
                return {'id': m.id, 'estado': m.estado, 'plan': m.plan.nombre, 'fecha_fin': m.fecha_fin}
        return None

    def validate_rut(self, valor):
        rut = _rut_normalizado(valor)
        qs = Socio.objects.filter(rut=rut)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un socio registrado con este RUT.")
        return rut

    def validate_telefono(self, valor):
        return _telefono_chileno(valor)

    def validate_nombres(self, valor):
        return _texto_nombre(valor, 'los nombres')

    def validate_apellidos(self, valor):
        return _texto_nombre(valor, 'los apellidos')

    def validate_email(self, valor):
        return valor.strip().lower() if valor else None


class RegistroAccesoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.SerializerMethodField()
    socio_rut = serializers.CharField(source='socio.rut', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcceso
        fields = ['id', 'socio', 'socio_nombre', 'socio_rut', 'fecha_hora_ingreso', 'fecha_hora_salida',
                  'permitido', 'motivo_rechazo', 'registrado_por_nombre']
        read_only_fields = fields

    def get_socio_nombre(self, obj):
        return f"{obj.socio.nombres} {obj.socio.apellidos}"

    def get_registrado_por_nombre(self, obj):
        return _nombre(obj.registrado_por)


class ValidarAccesoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=64, help_text="Token del QR o RUT del socio")


# ======================= PLANES, MEMBRESÍAS Y PAGOS =======================

class PlanSerializer(serializers.ModelSerializer):
    """Los planes son siempre mensuales: la duración la fija el servidor (30 días)."""

    class Meta:
        model = Plan
        fields = ['id', 'nombre', 'descripcion', 'duracion_dias', 'precio', 'activo']
        read_only_fields = ['id', 'duracion_dias']

    def validate_nombre(self, valor):
        return ' '.join(valor.split()).strip()

    def validate_precio(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a cero.")
        if valor != valor.to_integral_value():
            raise serializers.ValidationError("El precio debe ser un monto en pesos, sin decimales.")
        return valor

    def create(self, validated_data):
        validated_data['duracion_dias'] = DURACION_PLAN_DIAS
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['duracion_dias'] = DURACION_PLAN_DIAS
        return super().update(instance, validated_data)


class PagoSerializer(serializers.ModelSerializer):
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    usuario_responsable_nombre = serializers.SerializerMethodField()
    socio_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = ['id', 'membresia', 'monto', 'fecha_pago', 'metodo_pago', 'metodo_pago_display',
                  'comprobante_ref', 'usuario_responsable_nombre', 'socio_nombre']
        read_only_fields = fields

    def get_usuario_responsable_nombre(self, obj):
        return _nombre(obj.usuario_responsable)

    def get_socio_nombre(self, obj):
        s = obj.membresia.socio
        return f"{s.nombres} {s.apellidos}"


class MembresiaSerializer(serializers.ModelSerializer):
    """
    Para crear se envían `socio`, `plan` y opcionalmente `fecha_inicio`
    (hoy por defecto). Fecha de término, importe y estado son de solo
    lectura: los calcula el servidor a partir del plan.
    """
    socio = serializers.PrimaryKeyRelatedField(queryset=Socio.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    fecha_inicio = serializers.DateField(required=False)
    socio_nombre = serializers.SerializerMethodField()
    socio_rut = serializers.CharField(source='socio.rut', read_only=True)
    plan_nombre = serializers.CharField(source='plan.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()
    pago = serializers.SerializerMethodField()

    class Meta:
        model = Membresia
        fields = ['id', 'socio', 'socio_nombre', 'socio_rut', 'plan', 'plan_nombre',
                  'fecha_inicio', 'fecha_fin', 'importe_acordado', 'estado', 'estado_display',
                  'fecha_congelamiento', 'qr_enviado', 'registrado_por_nombre', 'pago']
        read_only_fields = ['id', 'fecha_fin', 'importe_acordado', 'estado',
                            'fecha_congelamiento', 'qr_enviado']

    def get_socio_nombre(self, obj):
        return f"{obj.socio.nombres} {obj.socio.apellidos}"

    def get_registrado_por_nombre(self, obj):
        return _nombre(obj.registrado_por)

    def get_pago(self, obj):
        pagos = list(obj.pagos.all())
        return PagoSerializer(pagos[0]).data if pagos else None


class RegistrarPagoSerializer(serializers.Serializer):
    metodo_pago = serializers.ChoiceField(choices=Pago.METODOS)
    comprobante_ref = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=['ACTIVA', 'CONGELADA', 'CANCELADA'])


# ======================= CLASES =======================

class TipoClaseSerializer(serializers.ModelSerializer):
    """Todas las actividades duran una hora: la duración la fija el servidor."""

    class Meta:
        model = TipoClase
        fields = ['id', 'nombre', 'descripcion', 'duracion_minutos', 'activa']
        read_only_fields = ['id', 'duracion_minutos']

    def validate_nombre(self, valor):
        return ' '.join(valor.split()).strip()

    def create(self, validated_data):
        validated_data['duracion_minutos'] = DURACION_CLASE_MINUTOS
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['duracion_minutos'] = DURACION_CLASE_MINUTOS
        return super().update(instance, validated_data)


class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ['id', 'nombre', 'ubicacion', 'capacidad_maxima', 'activa']

    def validate_capacidad_maxima(self, valor):
        if valor < 1 or valor > 200:
            raise serializers.ValidationError("La capacidad debe estar entre 1 y 200 personas.")
        return valor

    def validate_nombre(self, valor):
        return ' '.join(valor.split()).strip()


class SesionClaseSerializer(serializers.ModelSerializer):
    tipo_clase_nombre = serializers.CharField(source='tipo_clase.nombre', read_only=True)
    sala_nombre = serializers.CharField(source='sala.nombre', read_only=True)
    entrenador_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    inscritos_confirmados = serializers.IntegerField(read_only=True)
    en_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = SesionClase
        fields = ['id', 'tipo_clase', 'tipo_clase_nombre', 'entrenador', 'entrenador_nombre', 'sala',
                  'sala_nombre', 'fecha', 'hora_inicio', 'hora_fin', 'cupo_maximo', 'estado',
                  'estado_display', 'inscritos_confirmados', 'en_espera']
        read_only_fields = ['id', 'hora_fin']
        extra_kwargs = {'entrenador': {'required': False, 'allow_null': True}}

    def validate_hora_inicio(self, valor):
        if valor.minute or valor.second:
            raise serializers.ValidationError("Las clases comienzan a la hora en punto (ej: 07:00).")
        if not PRIMERA_HORA_INICIO <= valor.hour <= ULTIMA_HORA_INICIO:
            raise serializers.ValidationError(
                f"El horario de clases es de {PRIMERA_HORA_INICIO:02d}:00 a {ULTIMA_HORA_INICIO + 1:02d}:00."
            )
        return valor

    def get_entrenador_nombre(self, obj):
        return _nombre(obj.entrenador)

    def validate_entrenador(self, valor):
        if valor and (valor.rol != 'ENTRENADOR' or not valor.is_active):
            raise serializers.ValidationError("Debe seleccionar un entrenador activo.")
        return valor

    def validate(self, attrs):
        # La clase dura siempre una hora: la hora de término la calcula el servidor.
        hora_inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        if hora_inicio:
            attrs['hora_fin'] = (
                datetime.combine(timezone.localdate(), hora_inicio) + timedelta(minutes=DURACION_CLASE_MINUTOS)
            ).time()

        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo, None))

        entrenador = valor('entrenador')
        request = self.context.get('request')
        if request and request.user.rol == 'ENTRENADOR' and not request.user.is_superuser:
            entrenador = request.user  # la vista lo asigna como responsable de la clase

        errores = validar_horario_sesion(
            fecha=valor('fecha'), hora_inicio=valor('hora_inicio'), hora_fin=valor('hora_fin'),
            sala=valor('sala'), entrenador=entrenador, cupo_maximo=valor('cupo_maximo'),
            instancia=self.instance,
        )
        if errores:
            raise serializers.ValidationError(errores)
        return attrs


class InscripcionSerializer(serializers.ModelSerializer):
    socio = serializers.PrimaryKeyRelatedField(queryset=Socio.objects.filter(activo=True))
    sesion = serializers.PrimaryKeyRelatedField(queryset=SesionClase.objects.all())
    socio_nombre = serializers.SerializerMethodField()
    socio_rut = serializers.CharField(source='socio.rut', read_only=True)

    class Meta:
        model = InscripcionClase
        fields = ['id', 'socio', 'socio_nombre', 'socio_rut', 'sesion', 'fecha_inscripcion',
                  'asistio', 'en_espera']
        read_only_fields = ['id', 'fecha_inscripcion', 'asistio', 'en_espera']

    def get_socio_nombre(self, obj):
        return f"{obj.socio.nombres} {obj.socio.apellidos}"


# ======================= ENTRENADORES =======================

class EntrenadorSerializer(serializers.ModelSerializer):
    total_activos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'rut', 'first_name', 'last_name', 'email', 'telefono', 'especialidad',
                  'is_active', 'total_activos']
        read_only_fields = ['id', 'username', 'rut', 'first_name', 'last_name', 'email', 'telefono',
                            'is_active', 'total_activos']


class AsignacionSerializer(serializers.ModelSerializer):
    socio = serializers.PrimaryKeyRelatedField(queryset=Socio.objects.filter(activo=True))
    entrenador = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol='ENTRENADOR', is_active=True)
    )
    socio_nombre = serializers.SerializerMethodField()
    socio_rut = serializers.CharField(source='socio.rut', read_only=True)
    socio_telefono = serializers.CharField(source='socio.telefono', read_only=True)
    entrenador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = AsignacionEntrenador
        fields = ['id', 'socio', 'socio_nombre', 'socio_rut', 'socio_telefono', 'entrenador',
                  'entrenador_nombre', 'fecha_inicio', 'fecha_fin', 'activa']
        read_only_fields = ['id', 'fecha_inicio', 'fecha_fin', 'activa']

    def get_socio_nombre(self, obj):
        return f"{obj.socio.nombres} {obj.socio.apellidos}"

    def get_entrenador_nombre(self, obj):
        return _nombre(obj.entrenador)

    def validate(self, attrs):
        if AsignacionEntrenador.objects.filter(
            socio=attrs['socio'], entrenador=attrs['entrenador'], activa=True
        ).exists():
            raise serializers.ValidationError("El socio ya está asignado activamente a este entrenador.")
        return attrs


# ======================= EQUIPAMIENTO =======================

class EquipoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Equipo
        fields = ['id', 'codigo_unico', 'nombre', 'ubicacion', 'fecha_adquisicion', 'estado', 'estado_display']

    def validate_fecha_adquisicion(self, valor):
        if valor > timezone.localdate():
            raise serializers.ValidationError("La fecha de adquisición no puede ser futura.")
        return valor


class MantenimientoSerializer(serializers.ModelSerializer):
    equipo = serializers.PrimaryKeyRelatedField(queryset=Equipo.objects.all())
    usuario_responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Mantenimiento
        fields = ['id', 'equipo', 'fecha_programada', 'fecha_realizada', 'trabajo_realizado', 'costo',
                  'usuario_responsable_nombre']
        read_only_fields = ['id']

    def get_usuario_responsable_nombre(self, obj):
        return _nombre(obj.usuario_responsable)

    def validate_costo(self, valor):
        if valor < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return valor

    def validate_fecha_realizada(self, valor):
        if valor and valor > timezone.localdate():
            raise serializers.ValidationError("La fecha de ejecución no puede ser futura.")
        return valor


# ======================= GASTOS =======================

class CategoriaGastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaGasto
        fields = ['id', 'nombre', 'descripcion']


class GastoSerializer(serializers.ModelSerializer):
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaGasto.objects.all())
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    usuario_responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Gasto
        fields = ['id', 'categoria', 'categoria_nombre', 'concepto', 'importe', 'fecha', 'comprobante',
                  'usuario_responsable_nombre']
        read_only_fields = ['id']

    def get_usuario_responsable_nombre(self, obj):
        return _nombre(obj.usuario_responsable)

    def validate_importe(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("El importe debe ser mayor a cero.")
        return valor

    def validate_fecha(self, valor):
        if valor > timezone.localdate():
            raise serializers.ValidationError("No se pueden registrar gastos con fecha futura.")
        return valor
