# Guía de despliegue en AWS Academy — FitLife

Orden recomendado (cada paso depende del anterior):
**1 Security Groups → 2 RDS → 3 S3 → 4 EC2 Backend → 5 API Gateway → 6 EC2 Frontend → 7 CloudWatch + SNS → 8 Respaldos → 9 SAST/DAST**.

> Región: **us-east-1** (la del Learner Lab). En AWS Academy **no se pueden crear roles IAM**:
> usar **LabInstanceProfile** para las EC2 y **LabRole** para la Lambda.
> Al cerrar el laboratorio las EC2 se detienen y su **IP pública cambia** al volver a iniciarlas
> (ver "Si cambia la IP" al final).

Anota en un bloc de notas a medida que avanzas: endpoint RDS, nombre del bucket, IP/DNS de cada EC2,
URL de API Gateway, `SECRET_KEY` y `API_GATEWAY_SECRET`.

---

## 1. Security Groups (EC2 → Security Groups → Create)

> AWS no permite nombres que comiencen con `sg-` (prefijo reservado para los IDs).

| Nombre | Regla de entrada | Origen | Para qué |
|---|---|---|---|
| `fitlife-frontend-sg` | HTTP 80 | 0.0.0.0/0 | Usuarios abren la web |
| | SSH 22 | My IP | Administrar desde tu PC |
| | SSH 22 | 18.206.107.24/29 | Botón "Connect" del navegador (EC2 Instance Connect, us-east-1) |
| `fitlife-backend-sg` | HTTP 80 | 0.0.0.0/0 | API Gateway llama al backend (protegido con cabecera secreta) |
| | SSH 22 | My IP | Administrar desde tu PC |
| | SSH 22 | 18.206.107.24/29 | Botón "Connect" del navegador (EC2 Instance Connect, us-east-1) |
| `fitlife-rds-sg` | PostgreSQL 5432 | **fitlife-backend-sg** (el grupo, no una IP) | Solo el backend llega a la BD |

📸 Evidencia P3/P7: captura de las reglas de `fitlife-rds-sg` mostrando que el origen es el SG del backend.

## 2. RDS PostgreSQL (RDS → Create database)

- Standard create · **PostgreSQL** · plantilla **Free tier / Dev-Test** · `db.t3.micro` · 20 GB gp2/gp3.
- DB instance identifier: `fitlife-db` · usuario maestro: `fitlife_admin` · contraseña fuerte (anótala).
- Connectivity: **Public access: No** · VPC security group: **fitlife-rds-sg** (quitar el `default`).
- Additional configuration → Initial database name: `fitlife_db`.
- **Encryption: Enable encryption** (clave `aws/rds`). ⚠️ Se decide al crear; no se puede activar después
  sin migrar con un snapshot cifrado.
- **Backup**: Enable automated backups, retención **7 días**, ventana de respaldo a elección.
- Monitoring: dejar el básico.

TLS: en el `.env` del backend se usa `DB_SSLMODE=require` → el tráfico Django↔RDS va cifrado.

📸 Evidencia P7/P8: pestaña *Configuration* (Encryption: Enabled, KMS key) y *Maintenance & backups*.

## 3. S3 (S3 → Create bucket)

- Nombre único, ej.: `fitlife-estaticos-<tu-nombre>-2026`.
- **Block all public access: activado** (el bucket NO es público).
- Default encryption: **SSE-S3** (Bucket Key activado).
- Versioning: opcional (recomendado activarlo para poder recuperar archivos borrados).

El backend sube ahí los estáticos del admin/Swagger (`collectstatic`) y las imágenes QR. Los entrega con
**URL prefirmadas** que expiran en 1 hora. El permiso lo da el rol `LabInstanceProfile` de la EC2:
no hay claves de acceso en el código.

📸 Evidencia P7: *Permissions* (Block public access ON), *Properties* (Default encryption SSE-S3), un objeto
`media/qr/...png` y la URL prefirmada abierta desde la app (botón "Ver QR").

## 4. EC2 Backend

**Launch instance**: Ubuntu Server 24.04 · `t2.micro`/`t3.micro` · key pair `vockey` (o uno propio) ·
security group **fitlife-backend-sg** · *Advanced details → IAM instance profile*: **LabInstanceProfile**.

Conectarse por SSH (o EC2 Instance Connect) y ejecutar:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx git
cd ~
git clone <URL-de-tu-repositorio-backend> fitlife_backend    # o subir la carpeta con scp
cd fitlife_backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
nano .env
```

Contenido del `.env` en el servidor (reemplaza lo que está entre `< >`):

```ini
DEBUG=False
SECRET_KEY=<generar: python -c "from django.core.management.utils import get_random_secret_key as g; print(g())">
ALLOWED_HOSTS=<DNS-publico-ec2-backend>,<IP-publica-ec2-backend>
CSRF_TRUSTED_ORIGINS=http://<IP-publica-ec2-backend>
USAR_HTTPS=False
CORS_ALLOWED_ORIGINS=http://<IP-publica-ec2-frontend>
API_GATEWAY_SECRET=<texto-largo-aleatorio, ej: python -c "import secrets; print(secrets.token_urlsafe(32))">
ADMIN_URL=gestion-interna/

DB_NAME=fitlife_db
DB_USER=fitlife_admin
DB_PASSWORD=<la del paso 2>
DB_HOST=<endpoint-rds>.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_SSLMODE=require

USE_S3=True
AWS_STORAGE_BUCKET_NAME=<nombre-del-bucket>
AWS_S3_REGION_NAME=us-east-1
```

```bash
chmod 600 .env                                  # solo el dueño puede leer los secretos
python manage.py migrate                        # crea las tablas en RDS
python manage.py collectstatic --noinput        # sube estáticos a S3
python manage.py createsuperuser

sudo cp deploy/gunicorn-fitlife.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now gunicorn-fitlife
sudo cp deploy/nginx-backend.conf /etc/nginx/sites-available/fitlife-backend
sudo ln -sf /etc/nginx/sites-available/fitlife-backend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
crontab deploy/crontab.txt                      # vencimiento diario de membresías
```

> Si `ubuntu` no es tu usuario o la carpeta es otra, ajusta las rutas en `deploy/gunicorn-fitlife.service`.

Prueba: `curl http://<IP-backend>/api/health/` → `{"status":"ok"...}`
y `curl http://<IP-backend>/api/socios/` → **403 "Acceso directo no permitido"** (correcto: hay que pasar por API Gateway).

📸 Evidencia P3: la EC2 conectada a RDS (`python manage.py showmigrations` sin errores) y el 403 directo.

## 5. API Gateway (HTTP API) con rate limit

**Por qué HTTP API y no REST API**: es más simple y barata, tiene menor latencia y permite throttling por
etapa/ruta, que es lo que se exige. REST API agrega planes de uso, API keys, validación de requests y
WAF directo, que aquí no son necesarios.

1. API Gateway → **Create API → HTTP API → Build**.
2. Integrations: **HTTP** · Method `ANY` · URL `http://<DNS-publico-ec2-backend>/api/{proxy}` · nombre `fitlife-api`.
3. Routes: `ANY /api/{proxy+}`.
4. Stage: `$default` con **Auto-deploy**.
5. **Parameter mapping** de la integración (Integrations → la integración → *Parameter mapping* → Create):
   *Mapping type* **All incoming requests** → `Append` · `header.X-Gateway-Secret` · **Static value**: el mismo
   `API_GATEWAY_SECRET` del `.env`.
6. **Throttling**: Protect → Throttling → stage `$default` → Edit → **Rate 2** solicitudes/seg · **Burst 5**.
7. **CORS**: NO configurarlo en API Gateway (lo resuelve Django con `CORS_ALLOWED_ORIGINS`; si se configura en
   ambos lados, el navegador recibe cabeceras duplicadas).

URL resultante: `https://<id>.execute-api.us-east-1.amazonaws.com` → la API queda en `.../api/`.

**Prueba del rate limit** (desde tu PC o el CloudShell):

```bash
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}\n" https://<id>.execute-api.us-east-1.amazonaws.com/api/health/ & done; wait
```

Debes ver varios `429 Too Many Requests`. (Los límites son objetivos de throttling: no rechaza exactamente en
la solicitud 6.) Compara con la llamada directa a la EC2, que responde 403 a cualquier endpoint protegido.

📸 Evidencia P6: configuración de throttling (2/5), el parameter mapping y la terminal con los 429.

## 6. EC2 Frontend

Launch instance: Ubuntu 24.04 · `t2.micro` · **fitlife-frontend-sg**.

```bash
sudo apt update && sudo apt install -y nginx git curl
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
git clone <URL-de-tu-repositorio-frontend> fitlife_frontend && cd fitlife_frontend
echo "VITE_API_URL=https://<id>.execute-api.us-east-1.amazonaws.com/api" > .env
npm ci || npm install
npm run build
sudo mkdir -p /var/www/fitlife && sudo cp -r dist/* /var/www/fitlife/
sudo cp deploy/nginx-frontend.conf /etc/nginx/sites-available/fitlife-frontend
sudo ln -sf /etc/nginx/sites-available/fitlife-frontend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

> Si `npm run build` se queda sin memoria en `t2.micro`, compila en tu PC (`npm run build`) y sube la carpeta
> `dist/` con `scp -r dist ubuntu@<IP-frontend>:~/`.

Abre `http://<IP-frontend>`, inicia sesión y registra un socio. Verifica en RDS que se guardó
(desde la EC2 backend: `python manage.py shell -c "from socios.models import Socio; print(Socio.objects.last())"`).

📸 Evidencia P2: pestaña *Network* del navegador mostrando la llamada a `execute-api...` con
`Authorization: Bearer ...`, respuesta JSON 201 y el registro en la base de datos.

## 7. CloudWatch + SNS

1. SNS → Topics → Create **Standard** `fitlife-alertas` → Create subscription → **Email** → tu correo →
   confirma el correo que llega.
2. CloudWatch → Alarms → Create alarm → Select metric → **EC2 → Per-Instance Metrics → CPUUtilization**
   de la EC2 backend → *Average*, 5 minutos → **Greater than 70** → acción: notificar a `fitlife-alertas`.
3. (Opcional) Otra alarma: **RDS → FreeStorageSpace < 2 GB** o **DatabaseConnections**.
4. (Opcional) Dashboard `FitLife` con CPU de ambas EC2 y CPU/conexiones de RDS.

Métricas = números en el tiempo (CPU, red). Logs = texto de eventos (journalctl/gunicorn). Alarma = regla
sobre una métrica que dispara una acción (SNS).

📸 Evidencia P8: la alarma en estado OK/ALARM con su acción SNS, y la suscripción confirmada.

## 8. Respaldos

- **Automáticos (nativo RDS)**: ya activados en el paso 2 (retención 7 días + recuperación a un punto en el
  tiempo, *point-in-time restore*).
- **Snapshot manual**: RDS → la BD → Actions → **Take snapshot** → `fitlife-snapshot-manual-1`.
- **Cada 7 horas (ampliación)**: Lambda + EventBridge Scheduler.
  1. Lambda → Create function → Python 3.12 → rol existente **LabRole** → pegar `deploy/lambda_respaldo_rds.py`
     → Timeout 1 min → variables `DB_INSTANCE_ID=fitlife-db`, `SNS_TOPIC_ARN=<ARN de fitlife-alertas>`,
     `SNAPSHOTS_A_CONSERVAR=6` → *Test* para probarla.
  2. EventBridge → Scheduler → Create schedule → *Recurring* → **Rate-based: 7 hours** → target Lambda
     `fitlife-respaldo` → rol de ejecución **LabRole**.

Diferencias: el respaldo automático es diario y permite restaurar a cualquier segundo de los últimos N días;
el snapshot es una foto puntual que se conserva hasta borrarlo (sirve para migrar a una BD cifrada o clonar).
Recuperación: *Restore to point in time* o *Restore snapshot* → crea una **instancia nueva** y se cambia
`DB_HOST` en el `.env`.

📸 Evidencia P8: backups automáticos activos, lista de snapshots (manual + los de la Lambda), el schedule.

## 9. SAST y DAST

**SonarQube (SAST)** en tu PC:
```bash
docker run -d --name sonarqube -p 9000:9000 sonarqube:community
# entrar a http://localhost:9000 (admin/admin), crear proyecto local y token
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=<TOKEN>   # en la carpeta fitlife_backend
```
El archivo `sonar-project.properties` ya excluye migraciones, venv y estáticos. Documenta al menos un hallazgo
y su corrección o justificación.

**OWASP ZAP (DAST)** contra TU aplicación desplegada:
```bash
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://<IP-frontend> -r zap_frontend.html
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://<id>.execute-api.us-east-1.amazonaws.com/api/health/ -r zap_api.html
```
(Agrega `-v $(pwd):/zap/wrk/:rw` para obtener el reporte HTML en tu carpeta.)

---

## Si cambia la IP pública (al reiniciar el laboratorio)

1. Backend `.env`: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` (IP del frontend) →
   `sudo systemctl restart gunicorn-fitlife`.
2. API Gateway: editar la URL de la integración con el nuevo DNS del backend.
3. El frontend no cambia (usa la URL de API Gateway, que es fija).

Para evitarlo puedes asignar una **Elastic IP** a cada EC2 (si el laboratorio lo permite).

## Índice de evidencias sugerido (rúbrica)

| Código | Evidencia |
|---|---|
| P1 | `/api/docs/` (Swagger), pruebas CRUD en Postman/curl con códigos 200/201/204/400/405, `python manage.py test api` |
| P2 | Operación desde el frontend → petición a API Gateway → registro en RDS |
| P3 | 2 EC2 + RDS + S3 separados; Security Groups |
| P4 | Login JWT, 401 sin token, 403 por rol, refresh/logout; `.env` fuera de Git |
| P5 | Reporte SonarQube + reporte ZAP + comparación SAST/DAST |
| P6 | Throttling 2/5 en API Gateway + ráfaga con 429 + 403 en acceso directo |
| P7 | RDS cifrado + SG 5432 + TLS; S3 privado + SSE-S3 + URL prefirmada |
| P8 | Alarma CloudWatch + SNS; backups automáticos + snapshot (+ Lambda 7 h) |
| Cripto | `Usuario.objects.first().password` → `pbkdf2_sha256$...$salt$hash` |
