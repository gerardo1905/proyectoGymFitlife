from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from datetime import date
from usuarios.models import Usuario
from usuarios.decorators import rol_requerido
from .models import AsignacionEntrenador
from .forms import EspecialidadForm, AsignarSocioForm


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def entrenador_lista_view(request):
    entrenadores = Usuario.objects.filter(rol='ENTRENADOR').annotate(
        total_activos=Count('socios_asignados', filter=Q(socios_asignados__activa=True))
    ).order_by('first_name', 'last_name')
    return render(request, 'entrenadores/lista.html', {'entrenadores': entrenadores})


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def entrenador_detalle_view(request, pk):
    entrenador = get_object_or_404(Usuario, pk=pk, rol='ENTRENADOR')
    asignaciones_activas = entrenador.socios_asignados.filter(activa=True).select_related('socio').order_by('-fecha_inicio')
    asignaciones_historial = entrenador.socios_asignados.filter(activa=False).select_related('socio').order_by('-fecha_inicio')
    form = AsignarSocioForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        socio = form.cleaned_data['socio']

        # Evitar asignar dos veces activamente el mismo socio al mismo entrenador
        if AsignacionEntrenador.objects.filter(socio=socio, entrenador=entrenador, activa=True).exists():
            messages.error(request, f"{socio.nombres} {socio.apellidos} ya está asignado(a) activamente a este entrenador.")
        else:
            AsignacionEntrenador.objects.create(socio=socio, entrenador=entrenador)
            messages.success(request, f"{socio.nombres} {socio.apellidos} fue asignado(a) a {entrenador.first_name} {entrenador.last_name}.")
        return redirect('entrenador_detalle', pk=entrenador.pk)

    return render(request, 'entrenadores/detalle.html', {
        'entrenador': entrenador,
        'asignaciones_activas': asignaciones_activas,
        'asignaciones_historial': asignaciones_historial,
        'form': form,
    })


@login_required
@rol_requerido('ADMINISTRADOR')
def entrenador_editar_view(request, pk):
    entrenador = get_object_or_404(Usuario, pk=pk, rol='ENTRENADOR')
    form = EspecialidadForm(request.POST or None, instance=entrenador)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Especialidad de {entrenador.first_name} {entrenador.last_name} actualizada correctamente.")
        return redirect('entrenador_detalle', pk=entrenador.pk)

    return render(request, 'entrenadores/form.html', {
        'form': form,
        'entrenador': entrenador,
        'titulo': f'Editar Especialidad: {entrenador.first_name} {entrenador.last_name}'
    })


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def asignacion_finalizar_view(request, pk):
    asignacion = get_object_or_404(AsignacionEntrenador, pk=pk)
    if asignacion.activa:
        asignacion.activa = False
        asignacion.fecha_fin = date.today()
        asignacion.save()
        messages.info(request, f"Asignación de {asignacion.socio.nombres} {asignacion.socio.apellidos} finalizada.")
    return redirect('entrenador_detalle', pk=asignacion.entrenador.pk)


@login_required
@rol_requerido('ENTRENADOR')
def mis_socios_view(request):
    asignaciones_activas = request.user.socios_asignados.filter(activa=True).select_related('socio').order_by('-fecha_inicio')
    asignaciones_historial = request.user.socios_asignados.filter(activa=False).select_related('socio').order_by('-fecha_inicio')
    return render(request, 'entrenadores/mis_socios.html', {
        'asignaciones_activas': asignaciones_activas,
        'asignaciones_historial': asignaciones_historial,
    })
