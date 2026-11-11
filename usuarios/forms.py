from django import forms
from django.contrib.auth import get_user_model
from fitlife_config.validators import validador_telefono, sanitizar_y_validar_rut, sanitizar_telefono

Usuario = get_user_model()

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: admin.fitlife'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'ios-input', 'placeholder': '••••••••'})
    )


class UsuarioCrearForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'ios-input', 'placeholder': 'Mínimo 8 caracteres'})
    )
    telefono = forms.CharField(
        validators=[validador_telefono],
        required=False,
        widget=forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 912345678'}),
        label='Teléfono de Contacto'
    )

    class Meta:
        model = Usuario
        fields = ['username', 'rut', 'first_name', 'last_name', 'email', 'rol', 'telefono', 'password']
        labels = {
            'username': 'Nombre de Usuario',
            'rut': 'RUT del Trabajador',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Rol en el Sistema',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: carlos.silva'}),
            'rut': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 12.345.678-9 o 123456789'}),
            'first_name': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Carlos'}),
            'last_name': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Silva'}),
            'email': forms.EmailInput(attrs={'class': 'ios-input', 'placeholder': 'correo@fitlife.cl'}),
            'rol': forms.Select(attrs={'class': 'ios-input'}),
        }

    def clean_rut(self):
        rut_ingresado = self.cleaned_data.get('rut')
        rut_normalizado = sanitizar_y_validar_rut(rut_ingresado)
        if Usuario.objects.filter(rut=rut_normalizado).exists():
            raise forms.ValidationError("Ya existe un trabajador registrado con este RUT.")
        return rut_normalizado

    def clean_telefono(self):
        return sanitizar_telefono(self.cleaned_data.get('telefono'))

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip().title()

    def clean_last_name(self):
        return self.cleaned_data.get('last_name', '').strip().title()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UsuarioEditarForm(forms.ModelForm):
    telefono = forms.CharField(
        validators=[validador_telefono],
        required=False,
        widget=forms.TextInput(attrs={'class': 'ios-input'}),
        label='Teléfono de Contacto'
    )

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'rol', 'telefono', 'is_active']
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Rol en el Sistema',
            'is_active': 'Cuenta Activa',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'ios-input'}),
            'last_name': forms.TextInput(attrs={'class': 'ios-input'}),
            'email': forms.EmailInput(attrs={'class': 'ios-input'}),
            'rol': forms.Select(attrs={'class': 'ios-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'ios-checkbox'}),
        }

    def clean_telefono(self):
        return sanitizar_telefono(self.cleaned_data.get('telefono'))

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip().title()

    def clean_last_name(self):
        return self.cleaned_data.get('last_name', '').strip().title()


class PerfilEditarForm(forms.ModelForm):
    telefono = forms.CharField(
        validators=[validador_telefono],
        required=False,
        widget=forms.TextInput(attrs={'class': 'ios-input'}),
        label='Teléfono'
    )

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'ios-input'}),
            'last_name': forms.TextInput(attrs={'class': 'ios-input'}),
            'email': forms.EmailInput(attrs={'class': 'ios-input'}),
        }

    def clean_telefono(self):
        return sanitizar_telefono(self.cleaned_data.get('telefono'))

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip().title()

    def clean_last_name(self):
        return self.cleaned_data.get('last_name', '').strip().title()