# FitLife — Backend (API REST)

API REST del sistema de gestión del gimnasio **FitLife**, construida con **Django 4.2 + Django REST Framework**,
autenticación **JWT** y base de datos **PostgreSQL** (Amazon RDS en producción).

El backend **no tiene interfaz**: la aplicación web es el proyecto separado `fitlife_frontend` (React + Tailwind),
que se comunica con esta API mediante JSON a través de **Amazon API Gateway**.

## Arquitectura

```
Navegador ──► EC2 Frontend (Nginx + React) 
     │
     └── JSON + JWT ──► API Gateway (rate limit 2 rps / ráfaga 5) ──► EC2 Backend (Nginx → Gunicorn → Django REST)
                                                                         ├──► RDS PostgreSQL (privada, cifrada, TLS)
                                                                         └──► S3 (estáticos y QR, privado, SSE-S3, URL prefirmadas)
CloudWatch (métricas + alarma → SNS) · Lambda + EventBridge (snapshot RDS cada 7 h → SNS)
```

## Entidades (relacionadas)

`Usuario` (trabajador con rol) · `Socio` · `Plan` · `Membresia` (socio + plan) · `Pago` (membresía) ·
`RegistroAcceso` (socio) · `TipoClase` · `Sala` · `SesionClase` (tipo + sala + entrenador) ·
`InscripcionClase` (socio + sesión) · `AsignacionEntrenador` · `Equipo` · `Mantenimiento` · `CategoriaGasto` · `Gasto`.

## Endpoints principales (`/api/`)

Documentación interactiva (OpenAPI/Swagger): **`/api/docs/`**

| Recurso | Métodos | Notas |
|---|---|---|
| `auth/login/` | POST | `{username, password}` → `{access, refresh, usuario}` (limitado a 5/min) |
| `auth/refresh/` · `auth/logout/` | POST | Renovar token · invalidar refresh (lista negra) |
| `auth/perfil/` · `auth/cambiar-password/` | GET, PATCH · POST | Datos del usuario conectado |
| `socios/` | GET, POST, PUT, PATCH, DELETE | DELETE desactiva (conserva historial) |
| `planes/` | GET, POST, PUT, PATCH, DELETE | Escritura solo administrador |
| `membresias/` | GET, POST, DELETE | POST solo recibe `socio` y `plan`. Sin PUT: cambia por acciones |
| `membresias/{id}/pagar/` | POST | `{metodo_pago, comprobante_ref}` — el monto lo fija el servidor |
| `membresias/{id}/cambiar-estado/` | POST | `{estado: CONGELADA \| ACTIVA \| CANCELADA}` |
| `membresias/{id}/qr/` · `enviar-qr/` | GET · POST | URL prefirmada del QR (S3) · envío por correo |
| `pagos/` | GET | Solo lectura (registros contables) |
| `accesos/` · `accesos/validar/` · `accesos/{id}/salida/` | GET · POST · POST | Control de ingreso con QR o RUT |
| `sesiones/` · `inscripciones/` · `tipos-clase/` · `salas/` | CRUD | Cupos, lista de espera, choques de horario |
| `entrenadores/` · `asignaciones/` | GET, PATCH · GET, POST | |
| `equipos/` · `mantenimientos/` | CRUD | |
| `gastos/` · `categorias-gasto/` | CRUD | Solo administrador |
| `dashboard/` · `health/` | GET | Métricas · chequeo de salud |

Códigos HTTP: `200/201/204` éxito · `400` validación o regla de negocio · `401` sin token o token vencido ·
`403` rol sin permiso o acceso directo sin pasar por API Gateway · `404` · `405` método no permitido ·
`409` registro con datos asociados · `429` límite de solicitudes.

## Seguridad implementada

- **JWT** (SimpleJWT): access 30 min, refresh 10 h con rotación y lista negra al cerrar sesión.
- **Autorización por rol** (`api/permissions.py`): Administrador, Recepcionista, Entrenador.
- **Contraseñas** con hash **PBKDF2-SHA256 + salt** (nunca en texto plano) y validadores de robustez.
- **Rate limiting** en dos capas: API Gateway (principal) y DRF (`login` 5/min, anónimos 30/min).
- **Cabecera secreta de API Gateway** (`api/middleware.py`): quien llame directo a la IP de la EC2 recibe 403.
- **CORS** restringido a la URL del frontend.
- Secretos solo en variables de entorno (`.env`, fuera de Git). `DEBUG=False` en producción.
- Reglas de negocio en el servidor: fechas e importes calculados desde el plan, un solo pago por membresía,
  transiciones de estado controladas, validación del dígito verificador del RUT.

## Ejecución local

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # y completar los datos de PostgreSQL
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver       # API en http://localhost:8000/api/
python manage.py test api        # pruebas automatizadas
```

Despliegue en AWS: ver **[docs/GUIA_DESPLIEGUE_AWS.md](docs/GUIA_DESPLIEGUE_AWS.md)**.
