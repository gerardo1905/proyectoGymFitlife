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
                
            # Si el usuario es Entrenador y no seleccionó uno, autoasignarse a sí mismo
            if request.user.rol == 'ENTRENADOR' and not sesion.entrenador:
                sesion.entrenador = request.user
                
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
    inscritos = sesion.inscritos.select_related('socio').filter(en_espera=False)
    lista_espera = sesion.inscritos.select_related('socio').filter(en_espera=True)
    cupos_disponibles = sesion.cupo_maximo - inscritos.count()

    form_inscripcion = InscripcionSocioForm(request.POST or None)

    if request.method == 'POST' and form_inscripcion.is_valid():
        socio = form_inscripcion.cleaned_data['socio']

        # Validacion 1: Membresia Activa obligatoria
        membresia_activa = socio.membresias.filter(estado='ACTIVA', fecha_fin__gte=date.today()).exists()
        if not membresia_activa:
            messages.error(request, f"Rechazado: El socio {socio.nombres} no posee una membresía activa vigente.")
            return redirect('sesion_detalle', pk=sesion.pk)

        # Validacion 2: Evitar inscripcion duplicada (confirmada o en espera)
        if InscripcionClase.objects.filter(socio=socio, sesion=sesion).exists():
            messages.error(request, f"El socio {socio.nombres} ya está inscrito o en lista de espera de esta clase.")
            return redirect('sesion_detalle', pk=sesion.pk)

        # Validacion 3 y asignación de cupo/espera: Control Transaccional
        with transaction.atomic():
            sesion_bloqueada = SesionClase.objects.select_for_update().get(pk=pk)
            total_confirmados = sesion_bloqueada.inscritos.filter(en_espera=False).count()
            hay_cupo = total_confirmados < sesion_bloqueada.cupo_maximo

            InscripcionClase.objects.create(
                socio=socio,
                sesion=sesion_bloqueada,
                registrado_por=request.user,
                en_espera=not hay_cupo
            )

            if hay_cupo:
                messages.success(request, f"Socio {socio.nombres} inscrito exitosamente en {sesion.tipo_clase.nombre}.")
            else:
                posicion = sesion_bloqueada.inscritos.filter(en_espera=True).count()
                messages.info(
                    request,
                    f"Clase completa: {socio.nombres} fue agregado a la LISTA DE ESPERA en la posición N°{posicion}. "
                    f"Se le asignará un cupo automáticamente si alguien cancela su inscripción."
                )
            return redirect('sesion_detalle', pk=sesion.pk)

    context = {
        'sesion': sesion,
        'inscritos': inscritos,
        'lista_espera': lista_espera,
        'cupos_disponibles': cupos_disponibles,
        'form_inscripcion': form_inscripcion
    }
    return render(request, 'clases/sesion_detalle.html', context)

@login_required
@rol_requerido('ADMINISTRADOR', 'RECEPCIONISTA')
def inscripcion_cancelar_view(request, pk):
    with transaction.atomic():
        inscripcion = get_object_or_404(InscripcionClase.objects.select_for_update(), pk=pk)
        sesion_id = inscripcion.sesion.id
        socio_nombre = f"{inscripcion.socio.nombres} {inscripcion.socio.apellidos}"
        liberaba_cupo_confirmado = not inscripcion.en_espera
        inscripcion.delete()

        mensaje = f"Inscripción de {socio_nombre} cancelada."

        # Si quien se retira tenía cupo confirmado, se promueve automáticamente
        # al primero de la lista de espera (el más antiguo registrado).
        if liberaba_cupo_confirmado:
            siguiente_en_espera = InscripcionClase.objects.filter(
                sesion_id=sesion_id, en_espera=True
            ).order_by('fecha_inscripcion').first()

            if siguiente_en_espera:
                siguiente_en_espera.en_espera = False
                siguiente_en_espera.save()
                mensaje += (
                    f" Cupo liberado y asignado automáticamente a "
                    f"{siguiente_en_espera.socio.nombres} {siguiente_en_espera.socio.apellidos} "
                    f"(estaba en lista de espera)."
                )
            else:
                mensaje += " Cupo liberado."

    messages.info(request, mensaje)
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