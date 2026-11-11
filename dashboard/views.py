from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import date
from django.db.models import Sum

from socios.models import Socio, RegistroAcceso
from membresias.models import Membresia, Pago
from clases.models import SesionClase

@login_required
def home_view(request):
    # Si el usuario es entrenador, redirigir directamente a su agenda de clases
    if request.user.rol == 'ENTRENADOR':
        return redirect('sesion_lista')

    hoy = date.today()

    # 1. Métricas de Socios y Aforo
    total_socios_activos = Socio.objects.filter(activo=True).count()
    aforo_actual = RegistroAcceso.objects.filter(fecha_hora_salida__isnull=True, permitido=True).count()

    # 2. Métricas de Membresías y Recaudación
    membresias_activas = Membresia.objects.filter(estado='ACTIVA', fecha_fin__gte=hoy).count()
    ingresos_hoy = Pago.objects.filter(fecha_pago__date=hoy).aggregate(Sum('monto'))['monto__sum'] or 0

    # 3. Clases del Día
    clases_hoy = SesionClase.objects.filter(fecha=hoy).select_related('tipo_clase', 'sala').order_by('hora_inicio')

    # 4. Últimos Ingresos al Gimnasio (Torniquete)
    ultimos_accesos = RegistroAcceso.objects.select_related('socio').order_by('-fecha_hora_ingreso')[:5]

    context = {
        'total_socios_activos': total_socios_activos,
        'aforo_actual': aforo_actual,
        'membresias_activas': membresias_activas,
        'ingresos_hoy': ingresos_hoy,
        'clases_hoy': clases_hoy,
        'ultimos_accesos': ultimos_accesos,
        'hoy': hoy,
    }
    return render(request, 'dashboard/index.html', context)

def error_404_view(request, exception):
    return render(request, '404.html', status=404)