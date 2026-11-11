import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# 1. Validador de Teléfono: Solo permite números, espacios y prefijo +
validador_telefono = RegexValidator(
    regex=r'^\+?[0-9\s\-]{8,15}$',
    message="Ingrese un número de teléfono válido (solo números, mínimo 8 dígitos)."
)

# 2. Sanitizador y Validador Universal de RUT Chileno
def sanitizar_y_validar_rut(rut_raw):
    if not rut_raw:
        return rut_raw

    # Quitar puntos, guiones y espacios en blanco, transformar a mayúscula
    limpio = re.sub(r'[^0-9kK]', '', str(rut_raw)).upper()

    if len(limpio) < 8 or len(limpio) > 9:
        raise ValidationError("El RUT debe contener entre 8 y 9 dígitos (incluyendo dígito verificador).")

    cuerpo = limpio[:-1]
    dv = limpio[-1]

    # Formatear al estándar único de base de datos: XX.XXX.XXX-X
    if len(cuerpo) == 7:
        cuerpo_formateado = f"{cuerpo[0]}.{cuerpo[1:4]}.{cuerpo[4:7]}"
    else:
        cuerpo_formateado = f"{cuerpo[0:2]}.{cuerpo[2:5]}.{cuerpo[5:8]}"

    rut_estandar = f"{cuerpo_formateado}-{dv}"
    return rut_estandar


# 3. Sanitizador de Teléfonos (Guarda exclusivamente dígitos y prefijo +)
def sanitizar_telefono(telefono_raw):
    if not telefono_raw:
        return telefono_raw
    # Retener solo digitos y signo + inicial
    tiene_mas = str(telefono_raw).startswith('+')
    digitos = re.sub(r'[^0-9]', '', str(telefono_raw))
    return f"+{digitos}" if tiene_mas else digitos