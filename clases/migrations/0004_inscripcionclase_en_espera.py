# Generated manually to add the waiting-list support on InscripcionClase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clases', '0003_alter_inscripcionclase_fecha_inscripcion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcionclase',
            name='en_espera',
            field=models.BooleanField(default=False, verbose_name='En Lista de Espera'),
        ),
        migrations.AlterModelOptions(
            name='inscripcionclase',
            options={'ordering': ['fecha_inscripcion']},
        ),
    ]
