from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from datetime import date
from .models import Plan, Membresia, Pago
from .forms import PlanForm, MembresiaForm, PagoForm
from .utils import generar_imagen_qr, enviar_qr_por_correo
from socios.models import Socio
from usuarios.decorators import rol_requerido

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def plan_lista_view(request):
    planes = Plan.objects.all().order_by('-activo', 'nombre')
    return render(request, 'membresias/plan_lista.html', {'planes': planes})

@login_required
@rol_requerido('ADMINISTRADOR')
def plan_crear_view(request):
    form = PlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plan = form.save()
        messages.success(request, f"Plan '{plan.nombre}' creado exitosamente.")
        return redirect('plan_lista')
    return render(request, 'membresias/plan_form.html', {'form': form, 'titulo': 'Crear Nuevo Plan'})

@login_required
@rol_requerido('ADMINISTRADOR')
def plan_editar_view(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Plan '{plan.nombre}' actualizado correctamente.")
        return redirect('plan_lista')
    return render(request, 'membresias/plan_form.html', {'form': form, 'titulo': f'Editar Plan: {plan.nombre}'})


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def membresia_lista_view(request):
    estado_filtro = request.GET.get('estado', '').strip()
    busqueda = request.GET.get('q', '').strip()

    # Vencimiento automático
    hoy = date.today()
    Membresia.objects.filter(estado='ACTIVA', fecha_fin__lt=hoy).update(estado='VENCIDA')

    membresias = Membresia.objects.select_related('socio', 'plan', 'registrado_por').all().order_by('-fecha_inicio')

    if estado_filtro in ['ACTIVA', 'VENCIDA', 'CONGELADA', 'CANCELADA']:
        membresias = membresias.filter(estado=estado_filtro)

    if busqueda:
        membresias = membresias.filter(
            socio__rut__icontains=busqueda) | membresias.filter(
            socio__nombres__icontains=busqueda) | membresias.filter(
            socio__apellidos__icontains=busqueda)

    return render(request, 'membresias/membresia_lista.html', {
        'membresias': membresias,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
    })

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def membresia_crear_view(request, socio_id=None):
    socio_preseleccionado = get_object_or_404(Socio, pk=socio_id) if socio_id else None
    initial_data = {}
    if socio_preseleccionado:
        initial_data['socio'] = socio_preseleccionado

    form = MembresiaForm(request.POST or None, initial=initial_data)

    if request.method == 'POST' and form.is_valid():
        membresia = form.save(commit=False)
        membresia.registrado_por = request.user  # Guarda al trabajador en sesión
        membresia.save()

        # El mensaje de confirmacion y el envio del QR se disparan recien
        # cuando se registre el pago (ver pago_registrar_view), no aqui.
        return redirect('pago_registrar', membresia_id=membresia.pk)

    return render(request, 'membresias/membresia_form.html', {
        'form': form,
        'socio_preseleccionado': socio_preseleccionado,
        'titulo': f'Registrar Membresía — {socio_preseleccionado.nombres}' if socio_preseleccionado else 'Registrar Membresía'
    })

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def membresia_cambiar_estado_view(request, pk, nuevo_estado):
    membresia = get_object_or_404(Membresia, pk=pk)

    # Vuelve a la pagina desde donde se hizo clic (lista general o ficha del
    # socio); si no hay referer disponible, cae a la lista general como antes.
    siguiente_url = request.META.get('HTTP_REFERER')

    def _volver():
        return redirect(siguiente_url) if siguiente_url else redirect('membresia_lista')

    if nuevo_estado not in ['ACTIVA', 'VENCIDA', 'CONGELADA', 'CANCELADA']:
        return _volver()

    # Misma regla que MembresiaForm: un socio no puede tener mas de una
    # membresia "vigente" (ACTIVA o CONGELADA) al mismo tiempo. Se valida
    # aqui tambien porque este botón no pasa por el formulario.
    if nuevo_estado in ['ACTIVA', 'CONGELADA']:
        hay_conflicto = Membresia.objects.filter(
            socio=membresia.socio, estado__in=['ACTIVA', 'CONGELADA']
        ).exclude(pk=membresia.pk).exists()

        if hay_conflicto:
            messages.error(
                request,
                f"No se pudo marcar como '{nuevo_estado}': {membresia.socio.nombres} "
                f"{membresia.socio.apellidos} ya tiene otra membresía vigente. "
                "Cancélela o espere a que venza antes de activar/reactivar esta."
            )
            return _volver()

    membresia.estado = nuevo_estado
    membresia.save()
    messages.success(request, f"Membresía de {membresia.socio.nombres} actualizada a '{nuevo_estado}'.")
    return _volver()


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def pago_registrar_view(request, membresia_id):
    membresia = get_object_or_404(Membresia, pk=membresia_id)
    form = PagoForm(request.POST or None, initial={'monto': membresia.importe_acordado})

    if request.method == 'POST' and form.is_valid():
        pago = form.save(commit=False)
        pago.membresia = membresia
        pago.usuario_responsable = request.user
        pago.save()

        # Mensaje emergente de confirmacion de pago
        messages.success(
            request,
            f"Pago de ${pago.monto} registrado exitosamente a nombre de: {membresia.socio.nombres} {membresia.socio.apellidos}"
        )

        # Confirmacion de membresia activa y envio del QR: recien ahora,
        # porque el pago ya quedo efectivamente registrado.
        messages.success(
            request,
            f"Membresía activa a nombre de: {membresia.socio.nombres} {membresia.socio.apellidos}"
        )

        qr_enviado, mensaje_qr = enviar_qr_por_correo(membresia)
        if qr_enviado:
            messages.success(request, mensaje_qr)
        else:
            messages.warning(request, mensaje_qr)

        return redirect('socio_detalle', pk=membresia.socio.pk)

    return render(request, 'membresias/pago_form.html', {
        'form': form,
        'membresia': membresia,
        'titulo': f'Registrar Pago — Membresía #{membresia.id}'
    })


# ==================== CÓDIGO QR DE ACCESO LIGADO A LA MEMBRESÍA ====================

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def membresia_qr_ver_view(request, pk):
    """Sirve la imagen PNG del QR de la membresía (para verla o descargarla)."""
    membresia = get_object_or_404(Membresia, pk=pk)
    buffer = generar_imagen_qr(membresia)
    return HttpResponse(buffer.read(), content_type='image/png')


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def membresia_qr_reenviar_view(request, pk):
    """Reenvía manualmente el QR al correo del socio (útil si falló el envío automático)."""
    membresia = get_object_or_404(Membresia, pk=pk)
    qr_enviado, mensaje_qr = enviar_qr_por_correo(membresia)
    if qr_enviado:
        messages.success(request, mensaje_qr)
    else:
        messages.warning(request, mensaje_qr)
    return redirect('socio_detalle', pk=membresia.socio.pk)