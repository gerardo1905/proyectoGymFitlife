from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from datetime import date
from .models import TipoClase, Sala, SesionClase, InscripcionClase
from .forms import TipoClaseForm, SalaForm, SesionClaseForm, InscripcionSocioForm
from usuarios.decorators import rol_requerido

# ==================== ACTIVIDADES Y SALAS ====================

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA', 'ENTRENADOR')
def tipo_clase_lista_view(request):
    actividades = TipoClase.objects.all().order_by('nombre')
    salas = Sala.objects.all().order_by('nombre')
    return render(request, 'clases/tipo_clase_lista.html', {'actividades': actividades, 'salas': salas})

@login_required
@rol_requerido('ADMINISTRADOR')
def tipo_clase_crear_view(request):
    form = TipoClaseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        actividad = form.save()
        messages.success(request, f"Actividad '{actividad.nombre}' creada exitosamente.")
        return redirect('tipo_clase_lista')
    return render(request, 'clases/tipo_clase_form.html', {'form': form, 'titulo': 'Nueva Actividad Deportiva'})

@login_required
@rol_requerido('ADMINISTRADOR')
def sala_crear_view(request):
    form = SalaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sala = form.save()
        messages.success(request, f"Sala '{sala.nombre}' registrada correctamente.")
        return redirect('tipo_clase_lista')
    return render(request, 'clases/tipo_clase_form.html', {'form': form, 'titulo': 'Registrar Nueva Sala'})


# ==================== SESIONES Y RESERVA DE CUPOS ====================

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA', 'ENTRENADOR')
def sesion_lista_view(request):
    hoy = date.today()
    sesiones = SesionClase.objects.select_related('tipo_clase', 'sala', 'entrenador').filter(fecha__gte=hoy).order_by('fecha', 'hora_inicio')
    return render(request, 'clases/sesion_lista.html', {'sesiones': sesiones})


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA', 'ENTRENADOR')
def sesion_crear_view(request):
    form = SesionClaseForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            sesion = form.save(commit=False)
            
            # Asegurar estado por defecto
            if not sesion.estado:
                sesion.estado = 'PROGRAMADA'
                
            # Si el usuario es Entrenador y no seleccionó uno, autoasignar su perfil
            if request.user.rol == 'ENTRENADOR' and not sesion.entrenador and hasattr(request.user, 'perfil_entrenador'):
                sesion.entrenador = request.user.perfil_entrenador
                
            sesion.save()
            messages.success(request, f"Sesión de '{sesion.tipo_clase.nombre}' programada exitosamente.")
            return redirect('sesion_lista')
        else:
            print("❌ ERRORES DEL FORMULARIO:", form.errors.as_json())

    return render(request, 'clases/sesion_form.html', {'form': form, 'titulo': 'Programar Sesión de Clase'})


@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA', 'ENTRENADOR')
def sesion_detalle_view(request, pk):
    sesion = get_object_or_404(SesionClase.objects.select_related('tipo_clase', 'sala'), pk=pk)
    inscritos = sesion.inscritos.select_related('socio').all().order_by('fecha_inscripcion')
    cupos_disponibles = sesion.cupo_maximo - inscritos.count()
    
    form_inscripcion = InscripcionSocioForm(request.POST or None)

    if request.method == 'POST' and form_inscripcion.is_valid():
        socio = form_inscripcion.cleaned_data['socio']
        
        # Validacion 1: Membresia Activa obligatoria
        membresia_activa = socio.membresias.filter(estado='ACTIVA', fecha_fin__gte=date.today()).exists()
        if not membresia_activa:
            messages.error(request, f"Rechazado: El socio {socio.nombres} no posee una membresía activa vigente.")
            return redirect('sesion_detalle', pk=sesion.pk)

        # Validacion 2: Control Transaccional de Cupos
        with transaction.atomic():
            sesion_bloqueada = SesionClase.objects.select_for_update().get(pk=pk)
            total_inscritos = sesion_bloqueada.inscritos.count()

            if total_inscritos >= sesion_bloqueada.cupo_maximo:
                messages.error(request, "Rechazado: La clase ha alcanzado su cupo máximo de inscritos.")
                return redirect('sesion_detalle', pk=sesion.pk)

            # Validacion 3: Evitar inscripcion duplicada
            if InscripcionClase.objects.filter(socio=socio, sesion=sesion_bloqueada).exists():
                messages.error(request, f"El socio {socio.nombres} ya está inscrito en esta clase.")
                return redirect('sesion_detalle', pk=sesion.pk)

            InscripcionClase.objects.create(
                socio=socio,
                sesion=sesion_bloqueada,
                registrado_por=request.user
            )
            messages.success(request, f"Socio {socio.nombres} inscrito exitosamente en {sesion.tipo_clase.nombre}.")
            return redirect('sesion_detalle', pk=sesion.pk)

    context = {
        'sesion': sesion,
        'inscritos': inscritos,
        'cupos_disponibles': cupos_disponibles,
        'form_inscripcion': form_inscripcion
    }
    return render(request, 'clases/sesion_detalle.html', context)

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def inscripcion_cancelar_view(request, pk):
    inscripcion = get_object_or_404(InscripcionClase, pk=pk)
    sesion_id = inscripcion.sesion.id
    socio_nombre = f"{inscripcion.socio.nombres} {inscripcion.socio.apellidos}"
    inscripcion.delete()
    messages.info(request, f"Inscripción de {socio_nombre} cancelada. Cupo liberado.")
    return redirect('sesion_detalle', pk=sesion_id)

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA', 'ENTRENADOR')
def asistencia_marcar_view(request, pk):
    inscripcion = get_object_or_404(InscripcionClase, pk=pk)
    inscripcion.asistio = not inscripcion.asistio
    inscripcion.save()
    estado_texto = "Asistió" if inscripcion.asistio else "Ausente"
    messages.success(request, f"Asistencia de {inscripcion.socio.nombres} actualizada a '{estado_texto}'.")
    return redirect('sesion_detalle', pk=inscripcion.sesion.id)