from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .models import Usuario
from .forms import LoginForm, UsuarioCrearForm, UsuarioEditarForm, PerfilEditarForm
from .decorators import rol_requerido

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {user.first_name or user.username}!")
                return redirect('home')
            else:
                messages.error(request, "Esta cuenta de usuario se encuentra desactivada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'usuarios/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')

@login_required
def perfil_view(request):
    form = PerfilEditarForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Tu perfil ha sido actualizado correctamente.")
        return redirect('perfil')

    return render(request, 'usuarios/perfil.html', {'form': form})

@login_required
def cambiar_password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Tu contraseña ha sido actualizada con éxito.")
        return redirect('perfil')

    return render(request, 'usuarios/cambiar_password.html', {'form': form})

@login_required
@rol_requerido('ADMINISTRADOR')
def usuario_lista_view(request):
    trabajadores = Usuario.objects.all().order_by('-date_joined')
    return render(request, 'usuarios/lista.html', {'trabajadores': trabajadores})

@login_required
@rol_requerido('ADMINISTRADOR')
def usuario_crear_view(request):
    form = UsuarioCrearForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Nuevo trabajador registrado correctamente.")
        return redirect('usuario_lista')

    return render(request, 'usuarios/form_usuario.html', {'form': form, 'titulo': 'Registrar Nuevo Trabajador'})

@login_required
@rol_requerido('ADMINISTRADOR')
def usuario_editar_view(request, pk):
    trabajador = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=trabajador)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Datos de {trabajador.username} actualizados correctamente.")
        return redirect('usuario_lista')

    return render(request, 'usuarios/form_usuario.html', {'form': form, 'titulo': f'Editar Trabajador: {trabajador.username}'})


@login_required
@rol_requerido('ADMINISTRADOR')
def usuario_cambiar_password_view(request, pk):
    trabajador = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        nueva_clave = request.POST.get('password', '').strip()
        if len(nueva_clave) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        else:
            trabajador.set_password(nueva_clave)
            trabajador.save()
            messages.success(request, f"Contraseña de {trabajador.username} actualizada correctamente.")
            return redirect('usuario_lista')

    return render(request, 'usuarios/usuario_password_form.html', {'trabajador': trabajador})