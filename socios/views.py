from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date
from .models import Socio, RegistroAcceso
from .forms import SocioForm
from membresias.models import Membresia
from fitlife_config.validators import sanitizar_y_validar_rut
from usuarios.decorators import rol_requerido

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def socio_lista_view(request):
    query = request.GET.get('q', '').strip()
    socios = Socio.objects.all().order_by('-fecha_registro')

    if query:
        socios = socios.filter(
            Q(rut__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(email__icontains=query)
        )

    return render(request, 'socios/lista.html', {'socios': socios, 'query': query})

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def socio_detalle_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    membresias_historial = socio.membresias.all().order_by('-fecha_inicio')
    accesos_recientes = socio.accesos.all()[:10]
    
    return render(request, 'socios/detalle.html', {
        'socio': socio,
        'membresias': membresias_historial,
        'accesos': accesos_recientes
    })

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def socio_crear_view(request):
    form = SocioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        socio = form.save()
        messages.success(request, f"Socio {socio.nombres} {socio.apellidos} registrado exitosamente.")
        return redirect('socio_detalle', pk=socio.pk)

    return render(request, 'socios/form_socio.html', {'form': form, 'titulo': 'Registrar Nuevo Socio'})

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def socio_editar_view(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    form = SocioForm(request.POST or None, instance=socio)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Datos de {socio.nombres} {socio.apellidos} actualizados correctamente.")
        return redirect('socio_detalle', pk=socio.pk)

    return render(request, 'socios/form_socio.html', {'form': form, 'titulo': f'Editar Socio: {socio.nombres} {socio.apellidos}'})


# ==================== CONTROL DE ACCESO QR Y AFORO ====================

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def acceso_control_view(request):
    resultado_acceso = None
    rut_busqueda = request.POST.get('rut_qr', '').strip()

    if request.method == 'POST' and rut_busqueda:
        try:
            rut_normalizado = sanitizar_y_validar_rut(rut_busqueda)
            socio = Socio.objects.filter(rut=rut_normalizado).first()
        except Exception:
            socio = None

        if not socio:
            resultado_acceso = {
                'permitido': False,
                'motivo': f"RUT '{rut_busqueda}' no corresponde a ningún socio registrado.",
                'socio': None
            }
        elif not socio.activo:
            # Registrar Intento Fallido
            RegistroAcceso.objects.create(
                socio=socio,
                permitido=False,
                motivo_rechazo="Cuenta de Socio Inactiva",
                registrado_por=request.user
            )
            resultado_acceso = {
                'permitido': False,
                'motivo': f"Socio {socio.nombres} {socio.apellidos} se encuentra INACTIVO en la plataforma.",
                'socio': socio
            }
        else:
            # Verificar Membresía Activa Vigente
            hoy = date.today()
            membresia_vigente = Membresia.objects.filter(
                socio=socio,
                estado='ACTIVA',
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).first()

            if membresia_vigente:
                dias_restantes = (membresia_vigente.fecha_fin - hoy).days
                # Registrar Ingreso Exitoso
                RegistroAcceso.objects.create(
                    socio=socio,
                    permitido=True,
                    registrado_por=request.user
                )
                resultado_acceso = {
                    'permitido': True,
                    'socio': socio,
                    'membresia': membresia_vigente,
                    'dias_restantes': dias_restantes
                }
            else:
                # Registrar Rechazo por Membresía Impaga/Vencida
                RegistroAcceso.objects.create(
                    socio=socio,
                    permitido=False,
                    motivo_rechazo="Membresía Vencida o Inexistente",
                    registrado_por=request.user
                )
                resultado_acceso = {
                    'permitido': False,
                    'motivo': f"Socio {socio.nombres} {socio.apellidos} no cuenta con una membresía ACTIVA vigente.",
                    'socio': socio
                }

    # Calculo de Aforo en Tiempo Real (Socios adentro actualmente)
    personas_adentro = RegistroAcceso.objects.filter(
        permitido=True,
        fecha_hora_salida__isnull=True
    ).select_related('socio')

    historial_reciente = RegistroAcceso.objects.select_related('socio').all()[:15]

    return render(request, 'socios/acceso.html', {
        'resultado': resultado_acceso,
        'personas_adentro': personas_adentro,
        'aforo_actual': personas_adentro.count(),
        'historial': historial_reciente
    })

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def marcar_salida_view(request, pk):
    acceso = get_object_or_404(RegistroAcceso, pk=pk)
    if not acceso.fecha_hora_salida:
        acceso.fecha_hora_salida = timezone.now()
        acceso.save()
        messages.info(request, f"Salida de {acceso.socio.nombres} {acceso.socio.apellidos} registrada.")
    return redirect('acceso_control')