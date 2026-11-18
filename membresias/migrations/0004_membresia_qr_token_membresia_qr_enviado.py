# Generated manually to add the real QR-code support linked to each Membresia
#
# Se hace en 3 pasos porque la tabla ya tiene filas existentes: si se agrega
# directamente un UUIDField con default=uuid.uuid4 y unique=True, Django
# evalua el default UNA sola vez y lo repite en todas las filas existentes,
# lo que rompe la restriccion unica. Por eso primero se agrega sin unique,
# luego se rellena cada fila con un UUID distinto, y recien al final se
# activa la restriccion unique=True.

import uuid
from django.db import migrations, models


def generar_tokens_unicos(apps, schema_editor):
    Membresia = apps.get_model('membresias', 'Membresia')
    for membresia in Membresia.objects.all():
        membresia.qr_token = uuid.uuid4()
        membresia.save(update_fields=['qr_token'])


def revertir_tokens(apps, schema_editor):
    # No es necesario hacer nada al revertir: AddField/RemoveField se
    # encargan de quitar la columna completa.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('membresias', '0003_membresia_registrado_por_alter_membresia_estado'),
    ]

    operations = [
        # Paso 1: agregar el campo SIN unique todavia (permite valores repetidos
        # mientras se rellenan las filas existentes).
        migrations.AddField(
            model_name='membresia',
            name='qr_token',
            field=models.UUIDField(null=True, editable=False, verbose_name='Token único del Código QR'),
        ),
        migrations.AddField(
            model_name='membresia',
            name='qr_enviado',
            field=models.BooleanField(default=False, verbose_name='QR Enviado por Correo'),
        ),

        # Paso 2: rellenar cada fila existente con un UUID distinto.
        migrations.RunPython(generar_tokens_unicos, revertir_tokens),

        # Paso 3: ahora que todas las filas tienen un valor unico, se activa
        # la restriccion unique=True y el default para las membresias futuras.
        migrations.AlterField(
            model_name='membresia',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Token único del Código QR'),
        ),
    ]
