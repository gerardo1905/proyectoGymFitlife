from django import forms
from .models import Socio
from fitlife_config.validators import validador_telefono, sanitizar_y_validar_rut, sanitizar_telefono

class SocioForm(forms.ModelForm):
    # Aplicar validador estricto a nivel de formulario
    telefono = forms.CharField(
        validators=[validador_telefono],
        widget=forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 912345678'}),
        label='Teléfono de Contacto'
    )

    class Meta:
        model = Socio
        fields = ['rut', 'nombres', 'apellidos', 'email', 'telefono', 'contacto_emergencia', 'activo']
        labels = {
            'rut': 'RUT del Socio',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'email': 'Correo Electrónico',
            'contacto_emergencia': 'Contacto de Emergencia',
            'activo': 'Socio Activo (Permitir Contrataciones)',
        }
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 18.234.567-8 o 182345678'}),
            'nombres': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Juan Andrés'}),
            'apellidos': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Pérez Gómez'}),
            'email': forms.EmailInput(attrs={'class': 'ios-input', 'placeholder': 'ejemplo@correo.cl'}),
            'contacto_emergencia': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Nombre y Teléfono'}),
            'activo': forms.CheckboxInput(attrs={'class': 'ios-checkbox'}),
        }

    # Sanitización y Validación automática del RUT
    def clean_rut(self):
        rut_ingresado = self.cleaned_data.get('rut')
        rut_normalizado = sanitizar_y_validar_rut(rut_ingresado)
        
        # Verificar duplicados excluyendo el socio actual si se esta editando
        socio_id = self.instance.pk if self.instance else None
        if Socio.objects.filter(rut=rut_normalizado).exclude(pk=socio_id).exists():
            raise forms.ValidationError("Ya existe un socio registrado con este RUT en la base de datos.")
            
        return rut_normalizado

    # Sanitización automática del Teléfono
    def clean_telefono(self):
        telefono_ingresado = self.cleaned_data.get('telefono')
        return sanitizar_telefono(telefono_ingresado)

    # Limpieza de Nombres (Capitalizar palabras)
    def clean_nombres(self):
        return self.cleaned_data.get('nombres', '').strip().title()

    def clean_apellidos(self):
        return self.cleaned_data.get('apellidos', '').strip().title()