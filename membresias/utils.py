"""
Utilidades para generar el código QR ligado a una Membresia y enviarlo
por correo electrónico al Socio titular.

Diseño pensado para NUNCA interrumpir el flujo normal de creación de una
membresía: si el socio no tiene correo registrado, o el envío de correo
falla por cualquier motivo (credenciales SMTP no configuradas aún,
problema de red en el servidor, etc.), estas funciones devuelven un
resultado (ok, mensaje) para que la vista decida cómo informarlo, en vez
de lanzar una excepción que rompa la página.
"""
import io

import qrcode
from django.conf import settings
from django.core.mail import EmailMessage


def generar_imagen_qr(membresia):
    """
    Genera en memoria (sin tocar disco) la imagen PNG del código QR que
    codifica el token único de la membresía (membresia.qr_token).
    Retorna un BytesIO listo para adjuntar a un correo o servir como imagen.
    """
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(str(membresia.qr_token))
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    imagen.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def enviar_qr_por_correo(membresia):
    """
    Genera el QR de la membresía y lo envía por correo al socio.

    Retorna una tupla (ok: bool, mensaje: str) que la vista puede mostrar
    directamente con django.contrib.messages. Nunca lanza una excepción
    hacia arriba: cualquier error se captura y se informa como mensaje.
    """
    socio = membresia.socio

    if not socio.email:
        return False, (
            f"El socio {socio.nombres} no tiene un correo electrónico registrado; "
            f"no se pudo enviar el QR. Puedes agregarlo editando su ficha."
        )

    try:
        buffer = generar_imagen_qr(membresia)

        asunto = "Tu código de acceso FitLife 🏋️"
        cuerpo = (
            f"Hola {socio.nombres},\n\n"
            f"Este es tu código QR de acceso para el plan '{membresia.plan.nombre}', "
            f"vigente desde el {membresia.fecha_inicio.strftime('%d/%m/%Y')} "
            f"hasta el {membresia.fecha_fin.strftime('%d/%m/%Y')}.\n\n"
            f"Preséntalo en recepción (impreso o desde la pantalla de tu celular) "
            f"cada vez que ingreses al gimnasio.\n\n"
            f"¡Nos vemos en FitLife!"
        )

        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[socio.email],
        )
        email.attach(f"qr_fitlife_membresia_{membresia.pk}.png", buffer.read(), "image/png")
        email.send(fail_silently=False)

        membresia.qr_enviado = True
        membresia.save(update_fields=['qr_enviado'])
        return True, f"Código QR enviado correctamente a {socio.email}."

    except Exception as error:
        return False, (
            f"La membresía se guardó correctamente, pero no se pudo enviar el correo "
            f"con el QR (detalle técnico: {error}). Puedes reintentarlo luego desde "
            f"la ficha del socio."
        )
