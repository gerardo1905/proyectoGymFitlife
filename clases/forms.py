from django import forms
from datetime import date
from .models import TipoClase, Sala, SesionClase, InscripcionClase
from socios.models import Socio

class TipoClaseForm(forms.ModelForm):
    class Meta:
        model = TipoClase
        fields = ['nombre', 'descripcion', 'duracion_minutos', 'activa']
        labels = {
            'nombre': 'Nombre de la Actividad',
            'descripcion': 'Descripción del Entrenamiento',
            'duracion_minutos': 'Duración Habitual (Minutos)',
            'activa': 'Disponible en Oferta',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Spinning High Intensity'}),
            'descripcion': forms.Textarea(attrs={'class': 'ios-input', 'rows': 3, 'placeholder': 'Ej: Entrenamiento cardiovascular en bicicleta fija.'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 60'}),
            'activa': forms.CheckboxInput(attrs={'class': 'ios-checkbox'}),
        }


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nombre', 'ubicacion', 'capacidad_maxima', 'activa']
        labels = {
            'nombre': 'Nombre de la Sala',
            'ubicacion': 'Ubicación Interna',
            'capacidad_maxima': 'Capacidad Máxima (Aforo Persona)',
            'activa': 'Sala Habilitada',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Sala 1 - Fitness'}),
            'ubicacion': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Segundo Piso - Sector Oriente'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 20'}),
            'activa': forms.CheckboxInput(attrs={'class': 'ios-checkbox'}),
        }


class SesionClaseForm(forms.ModelForm):
    class Meta:
        model = SesionClase
        fields = ['tipo_clase', 'entrenador', 'sala', 'fecha', 'hora_inicio', 'hora_fin', 'cupo_maximo', 'estado']
        labels = {
            'tipo_clase': 'Actividad Deportiva',
            'entrenador': 'Entrenador a Cargo (Opcional)',
            'sala': 'Sala Reservada',
            'fecha': 'Fecha de la Sesión',
            'hora_inicio': 'Hora de Inicio',
            'hora_fin': 'Hora de Término',
            'cupo_maximo': 'Cupo Máximo de Inscritos',
            'estado': 'Estado de la Sesión',
        }
        widgets = {
            'tipo_clase': forms.Select(attrs={'class': 'ios-input'}),
            'entrenador': forms.Select(attrs={'class': 'ios-input'}),
            'sala': forms.Select(attrs={'class': 'ios-input'}),
            'fecha': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'ios-input', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'ios-input', 'type': 'time'}),
            'cupo_maximo': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 15'}),
            'estado': forms.Select(attrs={'class': 'ios-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_clase'].queryset = TipoClase.objects.filter(activa=True).order_by('nombre')
        self.fields['sala'].queryset = Sala.objects.filter(activa=True).order_by('nombre')
        
        # Opcionales al crear
        self.fields['entrenador'].required = False
        self.fields['estado'].required = False
        self.fields['estado'].initial = 'PROGRAMADA'
        
        if not self.instance.pk and not self.initial.get('fecha'):
            self.initial['fecha'] = date.today()

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        sala = cleaned_data.get('sala')
        cupo = cleaned_data.get('cupo_maximo')

        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise forms.ValidationError("La hora de término debe ser posterior a la hora de inicio.")

        if sala and cupo and cupo > sala.capacidad_maxima:
            raise forms.ValidationError(f"El cupo solicitado ({cupo}) supera la capacidad física de la {sala.nombre} ({sala.capacidad_maxima} personas).")

        return cleaned_data


class InscripcionSocioForm(forms.Form):
    socio = forms.ModelChoiceField(
        queryset=Socio.objects.none(),
        label="Seleccionar Socio",
        widget=forms.Select(attrs={'class': 'ios-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['socio'].queryset = Socio.objects.filter(activo=True).order_by('nombres')