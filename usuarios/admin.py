from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'rut', 'first_name', 'last_name', 'email', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username', 'rut', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol FitLife', {'fields': ('rol', 'rut', 'telefono')}),
    )