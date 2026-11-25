# Escrita a mano junto con la refactorización del flujo de membresías:
#  - Nuevo estado PENDIENTE (la membresía no se activa hasta registrar el pago).
#  - Campo fecha_congelamiento (para devolver los días congelados al socio).
#  - Pago.membresia pasa de CASCADE a PROTECT (no perder registros contables).
#  - Validadores de mínimos en Plan.duracion_dias y Plan.precio.

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membresias', '0004_membresia_qr_token_membresia_qr_enviado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membresia',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente de Pago'),
                    ('ACTIVA', 'Activa'),
                    ('VENCIDA', 'Vencida'),
                    ('CONGELADA', 'Congelada'),
                    ('CANCELADA', 'Cancelada'),
                ],
                default='PENDIENTE',
                max_length=20,
                verbose_name='Estado de Vigencia',
            ),
        ),
        migrations.AddField(
            model_name='membresia',
            name='fecha_congelamiento',
            field=models.DateField(blank=True, null=True, verbose_name='Congelada desde'),
        ),
        migrations.AlterField(
            model_name='pago',
            name='membresia',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagos',
                to='membresias.membresia',
                verbose_name='Membresía',
            ),
        ),
        migrations.AlterField(
            model_name='plan',
            name='duracion_dias',
            field=models.IntegerField(
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name='Duración (Días)',
            ),
        ),
        migrations.AlterField(
            model_name='plan',
            name='precio',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(Decimal('0'))],
                verbose_name='Precio',
            ),
        ),
    ]
