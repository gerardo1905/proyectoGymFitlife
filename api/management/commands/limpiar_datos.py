"""
Borra TODOS los datos de negocio del sistema (socios, membresías, pagos,
accesos, clases, entrenamientos, equipos, gastos, planes...), dejando la base
lista para empezar de cero. Por defecto CONSERVA las cuentas de trabajadores.

Uso:
    python manage.py limpiar_datos                       # pide confirmación, conserva trabajadores
    python manage.py limpiar_datos --incluir-trabajadores  # borra también los trabajadores (menos superusuarios)

⚠ No se puede deshacer. Haga un respaldo antes si los datos importan:
    pg_dump -U <usuario> -d fitlife_db -f respaldo.sql
"""
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from clases.models import InscripcionClase, SesionClase, TipoClase, Sala
from entrenadores.models import AsignacionEntrenador
from equipamiento.models import Mantenimiento, Equipo
from gastos.models import Gasto, CategoriaGasto
from membresias.models import Pago, Membresia, Plan, IngresoGimnasio
from rutinas.models import DetalleRutina, Rutina, Ejercicio
from socios.models import RegistroAcceso, Socio

# Orden importante: primero lo que depende de otras tablas (pagos antes que
# membresías, membresías antes que socios y planes, etc.).
MODELOS_EN_ORDEN = [
    ('Registros de acceso', RegistroAcceso),
    ('Ingresos (antiguo)', IngresoGimnasio),
    ('Inscripciones a clases', InscripcionClase),
    ('Sesiones de clase', SesionClase),
    ('Pagos', Pago),
    ('Membresías', Membresia),
    ('Asignaciones de entrenador', AsignacionEntrenador),
    ('Detalles de rutina', DetalleRutina),
    ('Rutinas', Rutina),
    ('Ejercicios', Ejercicio),
    ('Mantenciones', Mantenimiento),
    ('Equipos', Equipo),
    ('Gastos', Gasto),
    ('Categorías de gasto', CategoriaGasto),
    ('Socios', Socio),
    ('Planes', Plan),
    ('Actividades', TipoClase),
    ('Salas', Sala),
]


class Command(BaseCommand):
    help = "Borra todos los datos de negocio (conserva trabajadores salvo --incluir-trabajadores)."

    def add_arguments(self, parser):
        parser.add_argument('--incluir-trabajadores', action='store_true',
                            help="Borra también las cuentas de trabajadores (nunca los superusuarios).")
        parser.add_argument('--si', action='store_true', help="No pedir confirmación.")

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        self.stdout.write(self.style.WARNING("Se borrará lo siguiente:"))
        for nombre, modelo in MODELOS_EN_ORDEN:
            self.stdout.write(f"  - {nombre}: {modelo.objects.count()}")
        trabajadores = Usuario.objects.filter(is_superuser=False)
        if opciones['incluir_trabajadores']:
            self.stdout.write(f"  - Trabajadores (no superusuarios): {trabajadores.count()}")
        else:
            self.stdout.write("  (Se conservan las cuentas de trabajadores.)")

        if not opciones['si']:
            respuesta = input("\nEsta acción NO se puede deshacer. Escriba BORRAR para continuar: ")
            if respuesta.strip() != 'BORRAR':
                raise CommandError("Cancelado. No se borró nada.")

        with transaction.atomic():
            for nombre, modelo in MODELOS_EN_ORDEN:
                modelo.objects.all().delete()
            if opciones['incluir_trabajadores']:
                # Sesiones JWT de esos usuarios se borran en cascada.
                trabajadores.delete()

        # Imágenes QR generadas (local en media/qr o en S3).
        try:
            _, archivos = default_storage.listdir('qr')
            for archivo in archivos:
                default_storage.delete(f'qr/{archivo}')
        except (FileNotFoundError, OSError):
            pass

        self.stdout.write(self.style.SUCCESS("Listo: datos eliminados."))
