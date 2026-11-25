import io
from datetime import date

import qrcode
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count, Q, Sum, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from clases.models import TipoClase, Sala, SesionClase, InscripcionClase
from clases.services import inscribir_socio, cancelar_inscripcion
from entrenadores.models import AsignacionEntrenador
from equipamiento.models import Equipo, Mantenimiento
from gastos.models import CategoriaGasto, Gasto
from membresias import services as membresia_services
from membresias.models import Plan, Membresia, Pago
from membresias.services import ReglaNegocioError
from membresias.utils import enviar_qr_por_correo
from socios.models import Socio, RegistroAcceso
from socios.services import validar_ingreso
from fitlife_config.validators import sanitizar_y_validar_rut
from django.core.exceptions import ValidationError as DjangoValidationError
from . import serializers as s
from .permissions import PorRol, ADMIN, STAFF, TODOS, ENTRENADOR

Usuario = get_user_model()


def _param(request, nombre):
    return (request.query_params.get(nombre) or '').strip()


def _id_param(request, nombre):
    """Parámetro numérico de la URL; ignora valores inválidos en vez de provocar un error 500."""
    valor = _param(request, nombre)
    return int(valor) if valor.isdigit() else None


def _fecha_param(request, nombre):
    try:
        return date.fromisoformat(_param(request, nombre)) if _param(request, nombre) else None
    except ValueError:
        return None


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [PorRol]
    roles = STAFF


# ======================= AUTENTICACIÓN =======================

class LoginView(TokenObtainPairView):
    """POST {username, password} -> {access, refresh, usuario}. Limitado contra fuerza bruta."""
    serializer_class = s.LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(s.PerfilSerializer(request.user).data)

    def patch(self, request):
        serializer = s.PerfilSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = s.CambiarPasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['password_nueva'])
        request.user.save(update_fields=['password'])
        return Response({'detail': "Contraseña actualizada. Inicie sesión nuevamente."})


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    """Chequeo de salud (sin autenticación) para monitoreo."""
    return Response({'status': 'ok', 'hora_servidor': timezone.localtime().isoformat()})


# ======================= DASHBOARD =======================

class DashboardView(APIView):
    permission_classes = [PorRol]
    roles = STAFF

    def get(self, request):
        hoy = timezone.localdate()
        Membresia.actualizar_vencidas()
        clases_hoy = SesionClase.objects.filter(fecha=hoy).select_related(
            'tipo_clase', 'sala', 'entrenador').order_by('hora_inicio')
        return Response({
            'hoy': hoy,
            'total_socios_activos': Socio.objects.filter(activo=True).count(),
            'aforo_actual': RegistroAcceso.objects.filter(fecha_hora_salida__isnull=True, permitido=True).count(),
            'membresias_activas': Membresia.objects.filter(
                estado='ACTIVA', fecha_inicio__lte=hoy, fecha_fin__gte=hoy).count(),
            'membresias_pendientes': Membresia.objects.filter(estado='PENDIENTE').count(),
            'ingresos_hoy': Pago.objects.filter(fecha_pago__date=hoy).aggregate(t=Sum('monto'))['t'] or 0,
            'clases_hoy': s.SesionClaseSerializer(clases_hoy, many=True).data,
            'ultimos_accesos': s.RegistroAccesoSerializer(
                RegistroAcceso.objects.select_related('socio', 'registrado_por')[:5], many=True).data,
        })


# ======================= TRABAJADORES =======================

class UsuarioViewSet(BaseViewSet):
    """CRUD de trabajadores. DELETE desactiva la cuenta (no borra el historial asociado)."""
    serializer_class = s.UsuarioSerializer
    roles = (ADMIN,)

    def get_queryset(self):
        qs = Usuario.objects.all().order_by('-date_joined')
        if _param(self.request, 'rol'):
            qs = qs.filter(rol=_param(self.request, 'rol'))
        q = _param(self.request, 'q')
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) |
                           Q(last_name__icontains=q) | Q(rut__icontains=q))
        return qs

    def perform_update(self, serializer):
        trabajador = serializer.instance
        datos = serializer.validated_data
        if trabajador.pk == self.request.user.pk and (
            datos.get('rol', trabajador.rol) != trabajador.rol or datos.get('is_active', True) is False
        ):
            raise ReglaNegocioError("No puedes cambiar tu propio rol ni desactivar tu propia cuenta.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ReglaNegocioError("No puedes desactivar tu propia cuenta.")
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    @action(detail=True, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request, pk=None):
        trabajador = self.get_object()
        serializer = s.PasswordAdminSerializer(data=request.data, context={'trabajador': trabajador})
        serializer.is_valid(raise_exception=True)
        trabajador.set_password(serializer.validated_data['password'])
        trabajador.save(update_fields=['password'])
        return Response({'detail': f"Contraseña de {trabajador.username} actualizada."})


# ======================= SOCIOS =======================

class SocioViewSet(BaseViewSet):
    """CRUD de socios. DELETE desactiva al socio (conserva membresías, pagos y accesos)."""
    serializer_class = s.SocioSerializer

    def get_queryset(self):
        qs = Socio.objects.prefetch_related(
            Prefetch('membresias', queryset=Membresia.objects.select_related('plan').order_by('-fecha_fin'))
        ).order_by('-fecha_registro', '-pk')
        q = _param(self.request, 'q')
        if q:
            qs = qs.filter(Q(rut__icontains=q) | Q(nombres__icontains=q) |
                           Q(apellidos__icontains=q) | Q(email__icontains=q))
        if _param(self.request, 'activo') in ('true', 'false'):
            qs = qs.filter(activo=_param(self.request, 'activo') == 'true')
        if _param(self.request, 'sin_membresia') == 'true':
            # Disponibles para contratar: activos y sin membresía pendiente/activa/congelada.
            Membresia.actualizar_vencidas()
            qs = qs.filter(activo=True).exclude(membresias__estado__in=Membresia.ESTADOS_OCUPADOS)
        if _param(self.request, 'con_membresia_vigente') == 'true':
            hoy = timezone.localdate()
            qs = qs.filter(activo=True, membresias__estado='ACTIVA',
                           membresias__fecha_inicio__lte=hoy, membresias__fecha_fin__gte=hoy)
        if _param(self.request, 'rut'):
            # Búsqueda exacta (para avisar de RUT duplicado mientras se escribe).
            try:
                qs = qs.filter(rut=sanitizar_y_validar_rut(_param(self.request, 'rut')))
            except DjangoValidationError:
                qs = qs.none()
        return qs.distinct()

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=['activo'])

    @action(detail=True, methods=['get'])
    def accesos(self, request, pk=None):
        socio = self.get_object()
        return Response(s.RegistroAccesoSerializer(
            socio.accesos.select_related('registrado_por')[:20], many=True).data)


class AccesoViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = s.RegistroAccesoSerializer
    permission_classes = [PorRol]
    roles = STAFF

    def get_queryset(self):
        qs = RegistroAcceso.objects.select_related('socio', 'registrado_por')
        if _param(self.request, 'dentro') == 'true':
            qs = qs.filter(permitido=True, fecha_hora_salida__isnull=True)
        return qs

    @action(detail=False, methods=['post'])
    def validar(self, request):
        """POST {codigo}: token del QR o RUT. Devuelve si se permite el ingreso y por qué."""
        datos = s.ValidarAccesoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        r = validar_ingreso(datos.validated_data['codigo'], request.user)
        return Response({
            'permitido': r['permitido'],
            'motivo': r['motivo'],
            'socio': s.SocioSerializer(r['socio']).data if r['socio'] else None,
            'membresia': s.MembresiaSerializer(r['membresia']).data if r['membresia'] else None,
            'dias_restantes': r['dias_restantes'],
        })

    @action(detail=True, methods=['post'])
    def salida(self, request, pk=None):
        acceso = get_object_or_404(RegistroAcceso, pk=pk, permitido=True)
        if acceso.fecha_hora_salida:
            raise ReglaNegocioError("La salida de este ingreso ya fue registrada.")
        acceso.fecha_hora_salida = timezone.now()
        acceso.save(update_fields=['fecha_hora_salida'])
        return Response(s.RegistroAccesoSerializer(acceso).data)


# ======================= PLANES, MEMBRESÍAS Y PAGOS =======================

class PlanViewSet(BaseViewSet):
    serializer_class = s.PlanSerializer
    roles = STAFF
    roles_por_accion = {'create': (ADMIN,), 'update': (ADMIN,), 'partial_update': (ADMIN,), 'destroy': (ADMIN,)}

    def get_queryset(self):
        qs = Plan.objects.all().order_by('-activo', 'nombre')
        if _param(self.request, 'activo') == 'true':
            qs = qs.filter(activo=True)
        return qs


class MembresiaViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Sin PUT/PATCH a propósito: una membresía no se "edita", cambia de estado
    mediante acciones controladas (pagar, congelar, reactivar, cancelar).
    """
    serializer_class = s.MembresiaSerializer
    permission_classes = [PorRol]
    roles = STAFF

    def get_queryset(self):
        qs = Membresia.objects.select_related('socio', 'plan', 'registrado_por').prefetch_related(
            'pagos__usuario_responsable', 'pagos__membresia__socio'
        ).order_by('-fecha_inicio', '-pk')
        estado = _param(self.request, 'estado')
        if estado in dict(Membresia.ESTADOS):
            qs = qs.filter(estado=estado)
        if _id_param(self.request, 'socio'):
            qs = qs.filter(socio_id=_id_param(self.request, 'socio'))
        q = _param(self.request, 'q')
        if q:
            qs = qs.filter(Q(socio__rut__icontains=q) | Q(socio__nombres__icontains=q) |
                           Q(socio__apellidos__icontains=q))
        return qs

    def list(self, request, *args, **kwargs):
        Membresia.actualizar_vencidas()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membresia = membresia_services.crear_membresia(
            serializer.validated_data['socio'], serializer.validated_data['plan'], request.user,
            fecha_inicio=serializer.validated_data.get('fecha_inicio'),
        )
        return Response(self.get_serializer(membresia).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        membresia_services.eliminar_membresia(instance)

    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        """POST {metodo_pago, comprobante_ref}. El monto lo fija el servidor."""
        self.get_object()
        datos = s.RegistrarPagoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        membresia, _ = membresia_services.registrar_pago(
            pk, request.user, datos.validated_data['metodo_pago'], datos.validated_data.get('comprobante_ref')
        )
        enviado, mensaje_qr = enviar_qr_por_correo(membresia)
        membresia = self.get_queryset().get(pk=membresia.pk)
        return Response({'membresia': self.get_serializer(membresia).data,
                         'qr_enviado': enviado, 'mensaje_qr': mensaje_qr})

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """POST {estado: CONGELADA | ACTIVA | CANCELADA}"""
        self.get_object()
        datos = s.CambiarEstadoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        membresia_services.cambiar_estado(pk, datos.validated_data['estado'], request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=pk)).data)

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        """
        Devuelve una URL temporal (prefirmada si se usa S3) a la imagen del QR.
        El PNG se guarda en el almacenamiento configurado (S3 en AWS).
        """
        membresia = self.get_object()
        if membresia.estado not in ('ACTIVA', 'CONGELADA'):
            raise ReglaNegocioError("Solo las membresías activas o congeladas tienen QR de acceso.")
        ruta = f"qr/membresia_{membresia.pk}_{membresia.qr_token}.png"
        if not default_storage.exists(ruta):
            imagen = qrcode.make(str(membresia.qr_token))
            buffer = io.BytesIO()
            imagen.save(buffer, format='PNG')
            default_storage.save(ruta, ContentFile(buffer.getvalue()))
        url = default_storage.url(ruta)
        if url.startswith('/'):
            url = request.build_absolute_uri(url)
        return Response({'url': url})

    @action(detail=True, methods=['post'], url_path='enviar-qr')
    def enviar_qr(self, request, pk=None):
        membresia = self.get_object()
        if membresia.estado not in ('ACTIVA', 'CONGELADA'):
            raise ReglaNegocioError("Solo se puede enviar el QR de una membresía activa o congelada.")
        enviado, mensaje = enviar_qr_por_correo(membresia)
        return Response({'enviado': enviado, 'detail': mensaje},
                        status=status.HTTP_200_OK if enviado else status.HTTP_502_BAD_GATEWAY)


class PagoViewSet(viewsets.ReadOnlyModelViewSet):
    """Los pagos son registros contables: solo lectura (se crean con /membresias/{id}/pagar/)."""
    serializer_class = s.PagoSerializer
    permission_classes = [PorRol]
    roles = STAFF

    def get_queryset(self):
        qs = Pago.objects.select_related('membresia__socio', 'usuario_responsable').order_by('-fecha_pago')
        if _fecha_param(self.request, 'fecha'):
            qs = qs.filter(fecha_pago__date=_fecha_param(self.request, 'fecha'))
        return qs


# ======================= CLASES =======================

class TipoClaseViewSet(BaseViewSet):
    serializer_class = s.TipoClaseSerializer
    queryset = TipoClase.objects.all().order_by('nombre')
    roles = TODOS
    roles_por_accion = {'create': (ADMIN,), 'update': (ADMIN,), 'partial_update': (ADMIN,), 'destroy': (ADMIN,)}


class SalaViewSet(BaseViewSet):
    serializer_class = s.SalaSerializer
    queryset = Sala.objects.all().order_by('nombre')
    roles = TODOS
    roles_por_accion = {'create': (ADMIN,), 'update': (ADMIN,), 'partial_update': (ADMIN,), 'destroy': (ADMIN,)}


class SesionClaseViewSet(BaseViewSet):
    serializer_class = s.SesionClaseSerializer
    roles = TODOS
    roles_por_accion = {'destroy': (ADMIN,)}

    def get_queryset(self):
        qs = SesionClase.objects.select_related('tipo_clase', 'sala', 'entrenador').annotate(
            inscritos_confirmados=Count('inscritos', filter=Q(inscritos__en_espera=False)),
            en_espera=Count('inscritos', filter=Q(inscritos__en_espera=True)),
        ).order_by('fecha', 'hora_inicio')
        if _fecha_param(self.request, 'desde'):
            qs = qs.filter(fecha__gte=_fecha_param(self.request, 'desde'))
        elif self.action == 'list' and _param(self.request, 'historial') != 'true':
            qs = qs.filter(fecha__gte=timezone.localdate())
        if _param(self.request, 'mias') == 'true':
            qs = qs.filter(entrenador=self.request.user)
        return qs

    def _es_entrenador(self):
        return self.request.user.rol == ENTRENADOR and not self.request.user.is_superuser

    def perform_create(self, serializer):
        # Un entrenador solo programa clases a su propio nombre.
        if self._es_entrenador():
            serializer.save(entrenador=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if self._es_entrenador():
            if serializer.instance.entrenador_id != self.request.user.pk:
                raise ReglaNegocioError("Solo puedes modificar tus propias clases.")
            serializer.save(entrenador=self.request.user)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        if instance.inscritos.exists():
            raise ReglaNegocioError(
                "La sesión tiene socios inscritos. Cámbiela a estado 'Cancelada' en lugar de eliminarla."
            )
        instance.delete()

    @action(detail=True, methods=['get'])
    def inscritos(self, request, pk=None):
        sesion = self.get_object()
        qs = sesion.inscritos.select_related('socio').order_by('fecha_inscripcion')
        return Response(s.InscripcionSerializer(qs, many=True).data)


class InscripcionViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = s.InscripcionSerializer
    permission_classes = [PorRol]
    roles = STAFF
    roles_por_accion = {'asistencia': TODOS, 'list': TODOS, 'create': TODOS}

    def get_queryset(self):
        qs = InscripcionClase.objects.select_related('socio', 'sesion')
        if _id_param(self.request, 'sesion'):
            qs = qs.filter(sesion_id=_id_param(self.request, 'sesion'))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inscripcion = inscribir_socio(
            serializer.validated_data['sesion'].pk, serializer.validated_data['socio'], request.user
        )
        return Response(self.get_serializer(inscripcion).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        inscripcion = self.get_object()
        promovido = cancelar_inscripcion(inscripcion.pk)
        detalle = "Inscripción cancelada."
        if promovido:
            detalle += f" Cupo asignado a {promovido.socio.nombres} {promovido.socio.apellidos} (lista de espera)."
        return Response({'detail': detalle}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def asistencia(self, request, pk=None):
        inscripcion = self.get_object()
        if (request.user.rol == ENTRENADOR and not request.user.is_superuser
                and inscripcion.sesion.entrenador_id != request.user.pk):
            raise ReglaNegocioError("Solo puedes marcar asistencia en las clases que tú dictas.")
        if inscripcion.en_espera:
            raise ReglaNegocioError("No se puede marcar asistencia a alguien en lista de espera.")
        inscripcion.asistio = not inscripcion.asistio
        inscripcion.save(update_fields=['asistio'])
        return Response(self.get_serializer(inscripcion).data)


# ======================= ENTRENADORES =======================

class EntrenadorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    """Entrenadores = trabajadores con rol ENTRENADOR. Aquí solo se edita la especialidad."""
    serializer_class = s.EntrenadorSerializer
    permission_classes = [PorRol]
    roles = STAFF
    roles_por_accion = {'update': (ADMIN,), 'partial_update': (ADMIN,)}

    def get_queryset(self):
        return Usuario.objects.filter(rol=ENTRENADOR).annotate(
            total_activos=Count('socios_asignados', filter=Q(socios_asignados__activa=True))
        ).order_by('first_name', 'last_name')


class AsignacionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = s.AsignacionSerializer
    permission_classes = [PorRol]
    roles = STAFF
    roles_por_accion = {'list': (ADMIN, 'RECEPCIONISTA', ENTRENADOR)}

    def get_queryset(self):
        qs = AsignacionEntrenador.objects.select_related('socio', 'entrenador').order_by('-activa', '-fecha_inicio')
        # Un entrenador solo ve a sus propios socios.
        if self.request.user.rol == ENTRENADOR and not self.request.user.is_superuser:
            qs = qs.filter(entrenador=self.request.user)
        elif _id_param(self.request, 'entrenador'):
            qs = qs.filter(entrenador_id=_id_param(self.request, 'entrenador'))
        return qs

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        asignacion = self.get_object()
        if not asignacion.activa:
            raise ReglaNegocioError("La asignación ya estaba finalizada.")
        asignacion.activa = False
        asignacion.fecha_fin = timezone.localdate()
        asignacion.save(update_fields=['activa', 'fecha_fin'])
        return Response(self.get_serializer(asignacion).data)


# ======================= EQUIPAMIENTO =======================

class EquipoViewSet(BaseViewSet):
    serializer_class = s.EquipoSerializer
    roles = STAFF
    roles_por_accion = {'create': (ADMIN,), 'update': (ADMIN,), 'partial_update': (ADMIN,), 'destroy': (ADMIN,)}

    def get_queryset(self):
        qs = Equipo.objects.all().order_by('nombre')
        q = _param(self.request, 'q')
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_unico__icontains=q) | Q(ubicacion__icontains=q))
        return qs

    def perform_destroy(self, instance):
        if instance.mantenimientos.exists():
            raise ReglaNegocioError("El equipo tiene mantenciones registradas. Márquelo como 'Dado de Baja'.")
        instance.delete()


class MantenimientoViewSet(BaseViewSet):
    serializer_class = s.MantenimientoSerializer
    roles = STAFF
    roles_por_accion = {'destroy': (ADMIN,), 'update': (ADMIN,), 'partial_update': (ADMIN,)}

    def get_queryset(self):
        qs = Mantenimiento.objects.select_related('equipo', 'usuario_responsable').order_by('-fecha_programada')
        if _id_param(self.request, 'equipo'):
            qs = qs.filter(equipo_id=_id_param(self.request, 'equipo'))
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario_responsable=self.request.user)


# ======================= GASTOS =======================

class CategoriaGastoViewSet(BaseViewSet):
    serializer_class = s.CategoriaGastoSerializer
    queryset = CategoriaGasto.objects.all().order_by('nombre')
    roles = (ADMIN,)


class GastoViewSet(BaseViewSet):
    serializer_class = s.GastoSerializer
    roles = (ADMIN,)

    def get_queryset(self):
        qs = Gasto.objects.select_related('categoria', 'usuario_responsable').order_by('-fecha', '-pk')
        if _id_param(self.request, 'categoria'):
            qs = qs.filter(categoria_id=_id_param(self.request, 'categoria'))
        return qs

    def list(self, request, *args, **kwargs):
        respuesta = super().list(request, *args, **kwargs)
        total = self.filter_queryset(self.get_queryset()).aggregate(t=Sum('importe'))['t'] or 0
        if isinstance(respuesta.data, dict):
            respuesta.data['total_importe'] = total
        return respuesta

    def perform_create(self, serializer):
        serializer.save(usuario_responsable=self.request.user)
