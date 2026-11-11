from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from .models import Plan, Membresia, Pago
from .forms import PlanForm, MembresiaForm, PagoForm
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
        
        # Mensaje emergente de confirmacion
        messages.success(
            request, 
            f"Membresía activa a nombre de: {membresia.socio.nombres} {membresia.socio.apellidos}"
        )
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
    if nuevo_estado in ['ACTIVA', 'VENCIDA', 'CONGELADA', 'CANCELADA']:
        membresia.estado = nuevo_estado
        membresia.save()
        messages.success(request, f"Membresía de {membresia.socio.nombres} actualizada a '{nuevo_estado}'.")
    return redirect('membresia_lista')


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
        return redirect('socio_detalle', pk=membresia.socio.pk)

    return render(request, 'membresias/pago_form.html', {
        'form': form,
        'membresia': membresia,
        'titulo': f'Registrar Pago — Membresía #{membresia.id}'
    })