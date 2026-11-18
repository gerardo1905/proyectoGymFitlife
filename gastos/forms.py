from django import forms
from datetime import date
from .models import CategoriaGasto, Gasto


class CategoriaGastoForm(forms.ModelForm):
    class Meta:
        model = CategoriaGasto
        fields = ['nombre', 'descripcion']
        labels = {
            'nombre': 'Nombre de la Categoría',
            'descripcion': 'Descripción',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Mantenimiento de Equipos'}),
            'descripcion': forms.Textarea(attrs={'class': 'ios-input', 'rows': 2, 'placeholder': 'Ej: Gastos asociados a reparación y mantención de máquinas.'}),
        }


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['categoria', 'concepto', 'importe', 'fecha', 'comprobante']
        labels = {
            'categoria': 'Categoría',
            'concepto': 'Concepto / Detalle',
            'importe': 'Importe ($)',
            'fecha': 'Fecha del Gasto',
            'comprobante': 'Referencia de Comprobante (Opcional)',
        }
        widgets = {
            'categoria': forms.Select(attrs={'class': 'ios-input'}),
            'concepto': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Compra de artículos de limpieza'}),
            'importe': forms.NumberInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: 45000'}),
            'fecha': forms.DateInput(attrs={'class': 'ios-input', 'type': 'date'}),
            'comprobante': forms.TextInput(attrs={'class': 'ios-input', 'placeholder': 'Ej: Boleta #4521'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = CategoriaGasto.objects.all().order_by('nombre')
        self.fields['comprobante'].required = False
        if not self.instance.pk and not self.initial.get('fecha'):
            self.initial['fecha'] = date.today()
