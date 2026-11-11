from django import forms
from datetime import date
from .models import Plan, Membresia, Pago
from socios.models import Socio

class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['nombre', 'descripcion', 'duracion_dias', 'precio', 'activo']
        labels = {
            'nombre': 'Nombre del Plan',
            'descripcion': 'Descripción y Servicios Incluidos',
            'duracion_dias': 'Duración en Días',
            'precio': 'Precio ($ CLP)',
            'activo': 'Disponible para la Venta',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Mensual Full Gym'}),
            'descripcion': forms.Textarea(attrs={'class': 'ios-input', 'rows': 3, 'placeholder': 'Ej: Acceso libre a musculación y clases grupales.'}),
            'duracion_dias': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 30'}),
            'precio': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 35000'}),
            'activo': forms.CheckboxInput(attrs={'class': 'ios-checkbox'}),
        }


class MembresiaForm(forms.ModelForm):
    class Meta:
        model = Membresia
        fields = ['socio', 'plan', 'fecha_inicio', 'fecha_fin', 'importe_acordado', 'estado']
        labels = {
            'socio': 'Socio Titular',
            'plan': 'Plan a Contratar',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Término',
            'importe_acordado': 'Importe Acordado ($)',
            'estado': 'Estado de Vigencia',
        }
        widgets = {
            'socio': forms.Select(attrs={'class': 'ios-input'}),
            'plan': forms.Select(attrs={'class': 'ios-input'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'importe_acordado': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 35000'}),
            'estado': forms.Select(attrs={'class': 'ios-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['socio'].queryset = Socio.objects.filter(activo=True).order_by('nombres')
        self.fields['plan'].queryset = Plan.objects.filter(activo=True).order_by('nombre')
        if not self.instance.pk and not self.initial.get('fecha_inicio'):
            self.initial['fecha_inicio'] = date.today()

    def clean(self):
        cleaned_data = super().clean()
        socio = cleaned_data.get('socio')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        estado = cleaned_data.get('estado')

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise forms.ValidationError("La fecha de término debe ser posterior a la fecha de inicio.")

        # Validación estricta: Bloquear 2 membresías ACTIVAS simultáneas para el mismo socio
        if socio and estado == 'ACTIVA':
            membresias_activas = Membresia.objects.filter(
                socio=socio,
                estado='ACTIVA'
            )
            if self.instance.pk:
                membresias_activas = membresias_activas.exclude(pk=self.instance.pk)

            if membresias_activas.exists():
                raise forms.ValidationError(
                    f"El socio {socio.nombres} {socio.apellidos} ya cuenta con una membresía ACTIVA en curso. "
                    "Debe congelar, vencer o cancelar la anterior antes de registrar una nueva activa."
                )

        return cleaned_data


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto', 'metodo_pago', 'comprobante_ref']
        labels = {
            'monto': 'Monto a Pagar ($)',
            'metodo_pago': 'Método de Pago',
            'comprobante_ref': 'Nº Comprobante / Referencia (Opcional)',
        }
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 35000'}),
            'metodo_pago': forms.Select(attrs={'class': 'ios-input'}),
            'comprobante_ref': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Transbank #982341'}),
        }