import hmac

from django.conf import settings
from django.http import JsonResponse


class SoloDesdeApiGatewayMiddleware:
    """
    Si API_GATEWAY_SECRET está definido, toda petición a /api/ debe traer la
    cabecera X-Gateway-Secret con ese valor. API Gateway la agrega en cada
    solicitud (parameter mapping), así que quien llame directo a la IP de la
    EC2 recibe 403: el rate limit de API Gateway no se puede saltar.
    """

    RUTAS_LIBRES = ('/api/health/',)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        secreto = getattr(settings, 'API_GATEWAY_SECRET', '')
        if (
            secreto
            and request.path.startswith('/api/')
            and request.path not in self.RUTAS_LIBRES
        ):
            recibido = request.headers.get('X-Gateway-Secret', '')
            if not hmac.compare_digest(recibido.encode(), secreto.encode()):
                return JsonResponse(
                    {'detail': 'Acceso directo no permitido. Use la URL de API Gateway.'},
                    status=403,
                )
        return self.get_response(request)
