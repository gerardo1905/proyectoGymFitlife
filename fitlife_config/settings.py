import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde el archivo .env
load_dotenv(BASE_DIR / '.env')

def _env_bool(nombre, por_defecto='False'):
    return os.getenv(nombre, por_defecto).strip().lower() in ('1', 'true', 'yes', 'si', 'sí')


def _env_lista(nombre, por_defecto=''):
    return [v.strip() for v in os.getenv(nombre, por_defecto).split(',') if v.strip()]


# Configuraciones de seguridad desde .env
# DEBUG queda APAGADO salvo que el .env diga explícitamente DEBUG=True.
DEBUG = _env_bool('DEBUG', 'False')

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Desarrollo local sin .env: clave aleatoria en cada arranque (nunca escrita en el código).
        SECRET_KEY = get_random_secret_key()
    else:
        raise ImproperlyConfigured(
            "Falta SECRET_KEY en el archivo .env (obligatoria cuando DEBUG=False)."
        )

ALLOWED_HOSTS = _env_lista('ALLOWED_HOSTS', 'localhost,127.0.0.1')

# Ruta del admin de Django (cambiarla en producción dificulta ataques automatizados)
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')

# Orígenes desde donde se aceptan formularios POST (necesario detrás de un
# balanceador / Nginx o cuando se accede por IP pública o dominio).
# Ej: CSRF_TRUSTED_ORIGINS=http://54.12.34.56,https://fitlife.midominio.cl
CSRF_TRUSTED_ORIGINS = _env_lista('CSRF_TRUSTED_ORIGINS')

# Aplicaciones instaladas en el sistema
INSTALLED_APPS = [
    # Apps nativas de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Librerias de terceros
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'storages',

    # Aplicaciones modulares propias de FitLife
    'usuarios',
    'socios',
    'membresias',
    'clases',
    'entrenadores',
    'rutinas',
    'equipamiento',
    'gastos',
    'dashboard',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'api.middleware.SoloDesdeApiGatewayMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fitlife_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fitlife_config.wsgi.application'

# Conexion a PostgreSQL utilizando variables de entorno (.env).
# En AWS, DB_HOST será el endpoint de RDS o la IP privada de la instancia de BD.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'fitlife_db'),
        'USER': os.getenv('DB_USER', 'fitlife_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            # 'prefer' funciona en local; en RDS se puede forzar con DB_SSLMODE=require
            'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
        },
    }
}

# Validacion de contraseñas de Django
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Configuracion regional de idioma y zona horaria (Chile)
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Archivos estaticos y multimedia
STATIC_URL = '/static/'
# La interfaz vive en el proyecto fitlife_frontend; aquí solo quedan los estáticos del admin.
STATICFILES_DIRS = [d for d in [BASE_DIR / 'static'] if d.exists()]
STATIC_ROOT = BASE_DIR / 'static_root'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# En AWS los archivos (estáticos del admin/DRF y QR generados) se guardan en
# un bucket S3 PRIVADO con cifrado SSE-S3. Se accede mediante URL prefirmadas
# temporales, sin hacer público el bucket. En AWS Academy las credenciales
# las entrega el rol de la instancia (LabInstanceProfile): no se escriben claves.
USE_S3 = _env_bool('USE_S3', 'False')
if USE_S3:
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True          # URL prefirmadas
    AWS_QUERYSTRING_EXPIRE = 3600        # válidas por 1 hora
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {'ServerSideEncryption': 'AES256'}
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3.S3Storage', 'OPTIONS': {'location': 'media'}},
        'staticfiles': {'BACKEND': 'storages.backends.s3.S3Storage', 'OPTIONS': {'location': 'static'}},
    }

# Configuracion de correo (envio del QR de acceso al socio).
# Si EMAIL_HOST_USER/PASSWORD no estan definidos en el .env, el backend cae
# a "console" (imprime el correo en la terminal) en vez de fallar: esto
# permite que el resto del sistema funcione igual aunque aun no se hayan
# configurado las credenciales SMTP reales.
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'FitLife Gimnasio <noreply@fitlife.cl>')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Definicion del modelo de usuario personalizado para el personal de FitLife
AUTH_USER_MODEL = 'usuarios.Usuario'


# Seguridad de sesión
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 60 * 10  # 10 horas (un turno de recepción)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Cuando la app corre detrás de Nginx o de un balanceador de AWS que termina
# HTTPS, estas cabeceras le indican a Django la IP/protocolo real del cliente.
USE_X_FORWARDED_HOST = _env_bool('USE_X_FORWARDED_HOST', 'False')

# Activar SOLO cuando el sitio ya tenga certificado HTTPS funcionando.
if _env_bool('USAR_HTTPS', 'False'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', 'True')
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '3600'))

# Logs por consola (en el servidor los recoge systemd/journalctl o CloudWatch)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
}

# ============================================================
# API REST (Django REST Framework + JWT)
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'api.exceptions.manejador_excepciones',
    # Segunda capa de limitación (la primera es API Gateway).
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '30/min'),
        'user': os.getenv('THROTTLE_USER', '600/min'),
        'login': os.getenv('THROTTLE_LOGIN', '5/min'),   # contra fuerza bruta de contraseñas
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTOS', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=int(os.getenv('JWT_REFRESH_HORAS', '10'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,   # un refresh usado no se puede reutilizar
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FitLife API',
    'DESCRIPTION': 'API REST del sistema de gestión del gimnasio FitLife.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS: solo el frontend (su URL pública) puede llamar a la API desde el navegador.
CORS_ALLOWED_ORIGINS = _env_lista('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOW_HEADERS = ['accept', 'authorization', 'content-type', 'origin', 'x-requested-with']

# Secreto compartido con API Gateway (ver api/middleware.py). Vacío = desactivado (local).
API_GATEWAY_SECRET = os.getenv('API_GATEWAY_SECRET', '')

# Hash de contraseñas: el PRIMERO de la lista se usa para guardar contraseñas
# nuevas (PBKDF2-SHA256 con salt aleatorio y cientos de miles de iteraciones).
# Los siguientes solo sirven para verificar hashes antiguos, si existieran.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]
