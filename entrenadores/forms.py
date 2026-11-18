from django import forms
from usuarios.models import Usuario
from socios.models import Socio


class EspecialidadForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['especialidad']
        labels = {
            'especialidad': 'Especialidad Principal',
        }
        widgets = {
            'especialidad': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Musculación y Fuerza'}),
        }


class AsignarSocioForm(forms.Form):
    socio = forms.ModelChoiceField(
        queryset=Socio.objects.none(),
        label="Seleccionar Socio",
        widget=forms.Select(attrs={'class': 'ios-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['socio'].queryset = Socio.objects.filter(activo=True).order_by('nombres')
