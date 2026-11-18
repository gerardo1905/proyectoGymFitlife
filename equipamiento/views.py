from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from usuarios.decorators import rol_requerido
from .models import Equipo
from .forms import EquipoForm, MantenimientoForm


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def equipo_lista_view(request):
    query = request.GET.get('q', '').strip()
    equipos = Equipo.objects.all().order_by('nombre')

    if query:
        equipos = equipos.filter(
            Q(nombre__icontains=query) | Q(codigo_unico__icontains=query) | Q(ubicacion__icontains=query)
        )

    return render(request, 'equipamiento/lista.html', {'equipos': equipos, 'query': query})


@login_required
@rol_requerido('ADMINISTRADOR')
def equipo_crear_view(request):
    form = EquipoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        equipo = form.save()
        messages.success(request, f"Equipo '{equipo.nombre}' registrado correctamente.")
        return redirect('equipo_detalle', pk=equipo.pk)
    return render(request, 'equipamiento/form.html', {'form': form, 'titulo': 'Registrar Nuevo Equipo'})


@login_required
@rol_requerido('ADMINISTRADOR')
def equipo_editar_view(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    form = EquipoForm(request.POST or None, instance=equipo)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Equipo '{equipo.nombre}' actualizado correctamente.")
        return redirect('equipo_detalle', pk=equipo.pk)
    return render(request, 'equipamiento/form.html', {'form': form, 'titulo': f'Editar Equipo: {equipo.nombre}'})


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def equipo_detalle_view(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    mantenimientos = equipo.mantenimientos.select_related('usuario_responsable').order_by('-fecha_programada')
    form = MantenimientoForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mantenimiento = form.save(commit=False)
        mantenimiento.equipo = equipo
        mantenimiento.usuario_responsable = request.user
        mantenimiento.save()
        messages.success(request, f"Mantención registrada para '{equipo.nombre}'.")
        return redirect('equipo_detalle', pk=equipo.pk)

    return render(request, 'equipamiento/detalle.html', {
        'equipo': equipo,
        'mantenimientos': mantenimientos,
        'form': form,
    })
