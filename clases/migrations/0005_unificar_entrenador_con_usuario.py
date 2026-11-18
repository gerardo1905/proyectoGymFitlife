from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrar_entrenador_a_usuario(apps, schema_editor):
    """
    Copia, para cada SesionClase que ya tenga un Entrenador (modelo viejo de
    la app 'clases') asignado, el Usuario correspondiente al nuevo campo
    temporal 'entrenador_usuario'. Así ninguna sesión ya programada pierde
    su entrenador asignado al eliminar la tabla duplicada.
    """
    SesionClase = apps.get_model('clases', 'SesionClase')
    for sesion in SesionClase.objects.filter(entrenador__isnull=False).select_related('entrenador'):
        sesion.entrenador_usuario_id = sesion.entrenador.usuario_id
        sesion.save(update_fields=['entrenador_usuario'])


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0004_inscripcionclase_en_espera'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        # 1. Campo temporal que apunta directo al Usuario (Trabajador)
        migrations.AddField(
            model_name='sesionclase',
            name='entrenador_usuario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sesiones_dictadas_tmp',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # 2. Copiar el dato real de cada sesión ya programada (no se pierde nada)
        migrations.RunPython(migrar_entrenador_a_usuario, migrations.RunPython.noop),
        # 3. Eliminar el campo viejo (apuntaba a la tabla duplicada clases.Entrenador)
        migrations.RemoveField(
            model_name='sesionclase',
            name='entrenador',
        ),
        # 4. Eliminar la tabla duplicada: ya no la referencia nada
        migrations.DeleteModel(
            name='Entrenador',
        ),
        # 5. Dejar el campo temporal con el nombre definitivo 'entrenador'
        migrations.RenameField(
            model_name='sesionclase',
            old_name='entrenador_usuario',
            new_name='entrenador',
        ),
        # 6. Ajustar sus atributos finales (related_name definitivo + solo Usuarios con rol Entrenador)
        migrations.AlterField(
            model_name='sesionclase',
            name='entrenador',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sesiones_dictadas',
                limit_choices_to={'rol': 'ENTRENADOR'},
                to=settings.AUTH_USER_MODEL,
                verbose_name='Entrenador',
            ),
        ),
    ]
