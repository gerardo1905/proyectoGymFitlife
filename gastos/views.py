from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.db.models.deletion import RestrictedError
from usuarios.decorators import rol_requerido
from .models import CategoriaGasto, Gasto
from .forms import CategoriaGastoForm, GastoForm


@login_required
@rol_requerido('ADMINISTRADOR')
def gasto_lista_view(request):
    categoria_filtro = request.GET.get('categoria', '').strip()
    gastos = Gasto.objects.select_related('categoria', 'usuario_responsable').all().order_by('-fecha')

    if categoria_filtro:
        gastos = gastos.filter(categoria_id=categoria_filtro)

    total = gastos.aggregate(Sum('importe'))['importe__sum'] or 0
    categorias = CategoriaGasto.objects.all().order_by('nombre')

    return render(request, 'gastos/lista.html', {
        'gastos': gastos,
        'categorias': categorias,
        'categoria_filtro': categoria_filtro,
        'total': total,
    })


@login_required
@rol_requerido('ADMINISTRADOR')
def gasto_crear_view(request):
    form = GastoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        gasto = form.save(commit=False)
        gasto.usuario_responsable = request.user
        gasto.save()
        messages.success(request, f"Gasto '{gasto.concepto}' registrado correctamente.")
        return redirect('gasto_lista')
    return render(request, 'gastos/gasto_form.html', {'form': form, 'titulo': 'Registrar Nuevo Gasto'})


@login_required
@rol_requerido('ADMINISTRADOR')
def categoria_lista_view(request):
    categorias = CategoriaGasto.objects.all().order_by('nombre')
    return render(request, 'gastos/categoria_lista.html', {'categorias': categorias})


@login_required
@rol_requerido('ADMINISTRADOR')
def categoria_crear_view(request):
    form = CategoriaGastoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        categoria = form.save()
        messages.success(request, f"Categoría '{categoria.nombre}' creada correctamente.")
        return redirect('categoria_lista')
    return render(request, 'gastos/categoria_form.html', {'form': form, 'titulo': 'Nueva Categoría de Gasto'})


@login_required
@rol_requerido('ADMINISTRADOR')
def categoria_editar_view(request, pk):
    categoria = get_object_or_404(CategoriaGasto, pk=pk)
    form = CategoriaGastoForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Categoría '{categoria.nombre}' actualizada correctamente.")
        return redirect('categoria_lista')
    return render(request, 'gastos/categoria_form.html', {'form': form, 'titulo': f'Editar Categoría: {categoria.nombre}'})


@login_required
@rol_requerido('ADMINISTRADOR')
def categoria_eliminar_view(request, pk):
    categoria = get_object_or_404(CategoriaGasto, pk=pk)
    nombre = categoria.nombre
    try:
        categoria.delete()
        messages.success(request, f"Categoría '{nombre}' eliminada correctamente.")
    except RestrictedError:
        total_gastos = categoria.gastos.count()
        messages.error(
            request,
            f"No se puede eliminar '{nombre}' porque tiene {total_gastos} gasto(s) registrado(s) asociado(s). "
            "Elimina o reasigna esos gastos a otra categoría primero."
        )
    return redirect('categoria_lista')
