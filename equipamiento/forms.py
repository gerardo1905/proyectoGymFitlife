from django import forms
from datetime import date
from .models import Equipo, Mantenimiento


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['codigo_unico', 'nombre', 'ubicacion', 'fecha_adquisicion', 'estado']
        labels = {
            'codigo_unico': 'Código de Equipo',
            'nombre': 'Nombre de la Máquina / Accesorio',
            'ubicacion': 'Ubicación en el Gimnasio',
            'fecha_adquisicion': 'Fecha de Adquisición',
            'estado': 'Estado Actual',
        }
        widgets = {
            'codigo_unico': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: MAQ-001'}),
            'nombre': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Cinta de Trote Technogym'}),
            'ubicacion': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Sala de Cardio'}),
            'fecha_adquisicion': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'ios-input'}),
        }


class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = ['fecha_programada', 'fecha_realizada', 'trabajo_realizado', 'costo']
        labels = {
            'fecha_programada': 'Fecha Programada',
            'fecha_realizada': 'Fecha de Ejecución (Opcional)',
            'trabajo_realizado': 'Trabajo Realizado',
            'costo': 'Costo ($)',
        }
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'fecha_realizada': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'trabajo_realizado': forms.Textarea(attrs={'class': 'ios-input', 'rows': 2, 'placeholder': 'Ej: Cambio de correa y lubricación de motor.'}),
            'costo': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 25000'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_realizada'].required = False
        self.fields['trabajo_realizado'].required = False
        if not self.instance.pk and not self.initial.get('fecha_programada'):
            self.initial['fecha_programada'] = date.today()
