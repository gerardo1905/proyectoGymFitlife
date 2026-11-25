"""
Pruebas de la API REST: autenticación JWT, autorización por rol y reglas
de negocio de membresías, pagos y control de acceso.

Ejecutar con:
    python manage.py test api
"""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from fitlife_config.validators import sanitizar_y_validar_rut
from membresias.models import Plan, Membresia, Pago
from socios.models import Socio, RegistroAcceso
from usuarios.models import Usuario

PASSWORD = 'ClaveSegura#2026'


class BaseAPITest(APITestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.admin = Usuario.objects.create_user(
            username='admin_test', password=PASSWORD, rut='11.111.111-1', rol='ADMINISTRADOR')
        self.recepcion = Usuario.objects.create_user(
            username='recep_test', password=PASSWORD, rut='12.345.678-5', rol='RECEPCIONISTA')
        self.entrenador = Usuario.objects.create_user(
            username='coach_test', password=PASSWORD, rut='9.876.543-3', rol='ENTRENADOR')
        self.socio = Socio.objects.create(
            rut='7.654.321-6', nombres='Ana', apellidos='Pérez', telefono='912345678', email='ana@test.cl')
        self.plan = Plan.objects.create(nombre='Mensual', duracion_dias=30, precio=Decimal('35000'))
        self.client.force_authenticate(self.recepcion)

    def crear_membresia(self, **extra):
        datos = {'socio': self.socio.pk, 'plan': self.plan.pk, **extra}
        return self.client.post('/api/membresias/', datos, format='json')

    def pagar(self, membresia_id, metodo='EFECTIVO', comprobante='', **extra):
        datos = {'metodo_pago': metodo, 'comprobante_ref': comprobante, **extra}
        return self.client.post(f'/api/membresias/{membresia_id}/pagar/', datos, format='json')


class AutenticacionTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(None)

    def test_sin_token_responde_401(self):
        self.assertEqual(self.client.get('/api/socios/').status_code, 401)

    def test_login_entrega_jwt_y_permite_acceder(self):
        r = self.client.post('/api/auth/login/', {'username': 'recep_test', 'password': PASSWORD}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.assertEqual(r.data['usuario']['rol'], 'RECEPCIONISTA')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(self.client.get('/api/socios/').status_code, 200)

    def test_password_guardada_con_hash(self):
        self.assertNotEqual(self.admin.password, PASSWORD)
        self.assertTrue(self.admin.password.startswith('pbkdf2_sha256$'))


class AutorizacionTests(BaseAPITest):
    def test_recepcionista_no_ve_gastos(self):
        self.assertEqual(self.client.get('/api/gastos/').status_code, 403)

    def test_entrenador_no_ve_socios(self):
        self.client.force_authenticate(self.entrenador)
        self.assertEqual(self.client.get('/api/socios/').status_code, 403)


class SocioTests(BaseAPITest):
    def test_crud_socio_y_validacion_rut(self):
        r = self.client.post('/api/socios/', {
            'rut': '123456785', 'nombres': 'juan', 'apellidos': 'soto', 'telefono': '987654321'
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['rut'], '12.345.678-5')
        self.assertEqual(r.data['nombres'], 'Juan')

        r = self.client.patch(f"/api/socios/{r.data['id']}/", {'email': 'juan@test.cl'}, format='json')
        self.assertEqual(r.status_code, 200)

        r = self.client.post('/api/socios/', {
            'rut': '12.345.678-9', 'nombres': 'x', 'apellidos': 'y', 'telefono': '987654321'
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('rut', r.data)

    def test_delete_desactiva_al_socio(self):
        r = self.client.delete(f'/api/socios/{self.socio.pk}/')
        self.assertEqual(r.status_code, 204)
        self.socio.refresh_from_db()
        self.assertFalse(self.socio.activo)


class MembresiaTests(BaseAPITest):
    def test_fechas_e_importe_los_calcula_el_servidor(self):
        r = self.crear_membresia(fecha_fin='2099-12-31', importe_acordado='1', estado='ACTIVA')  # se ignoran
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['estado'], 'PENDIENTE')
        self.assertEqual(Decimal(r.data['importe_acordado']), Decimal('35000'))
        m = Membresia.objects.get(pk=r.data['id'])
        self.assertEqual(m.fecha_fin, self.hoy + timedelta(days=29))

    def test_fecha_de_inicio_futura_cuenta_30_dias_y_no_deja_entrar_antes(self):
        inicio = self.hoy + timedelta(days=10)
        r = self.crear_membresia(fecha_inicio=inicio.isoformat())
        self.assertEqual(r.status_code, 201, r.data)
        self.pagar(r.data['id'])
        m = Membresia.objects.get(pk=r.data['id'])
        self.assertEqual(m.estado, 'ACTIVA')
        self.assertEqual(m.fecha_inicio, inicio)
        self.assertEqual(m.fecha_fin, inicio + timedelta(days=29))
        acceso = self.client.post('/api/accesos/validar/', {'codigo': str(m.qr_token)}, format='json')
        self.assertFalse(acceso.data['permitido'])
        self.assertIn('comienza', acceso.data['motivo'])

    def test_fecha_de_inicio_pasada_o_muy_lejana_se_rechaza(self):
        self.assertEqual(self.crear_membresia(fecha_inicio=(self.hoy - timedelta(days=1)).isoformat()).status_code, 400)
        self.assertEqual(self.crear_membresia(fecha_inicio=(self.hoy + timedelta(days=61)).isoformat()).status_code, 400)

    def test_no_permite_segunda_membresia_en_curso(self):
        self.crear_membresia()
        self.assertEqual(self.crear_membresia().status_code, 400)

    def test_pago_activa_con_monto_fijo_y_una_sola_vez(self):
        mid = self.crear_membresia().data['id']
        r = self.pagar(mid, monto='1')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['membresia']['estado'], 'ACTIVA')
        self.assertEqual(Pago.objects.get(membresia_id=mid).monto, Decimal('35000'))
        self.assertEqual(self.pagar(mid).status_code, 400)
        self.assertEqual(Pago.objects.filter(membresia_id=mid).count(), 1)

    def test_tarjeta_exige_comprobante(self):
        mid = self.crear_membresia().data['id']
        self.assertEqual(self.pagar(mid, metodo='DEBITO').status_code, 400)

    def test_recepcionista_no_cancela_pagada_pero_admin_si(self):
        mid = self.crear_membresia().data['id']
        self.pagar(mid)
        url = f'/api/membresias/{mid}/cambiar-estado/'
        self.assertEqual(self.client.post(url, {'estado': 'CANCELADA'}, format='json').status_code, 400)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(url, {'estado': 'CANCELADA'}, format='json').status_code, 200)
        # Una cancelada no se puede reactivar.
        self.assertEqual(self.client.post(url, {'estado': 'ACTIVA'}, format='json').status_code, 400)

    def test_descongelar_devuelve_los_dias(self):
        mid = self.crear_membresia().data['id']
        self.pagar(mid)
        m = Membresia.objects.get(pk=mid)
        fin_original = m.fecha_fin
        m.congelar(fecha=self.hoy - timedelta(days=10))
        m.descongelar(fecha=self.hoy)
        self.assertEqual(m.fecha_fin, fin_original + timedelta(days=10))

    def test_no_existe_put_en_membresias(self):
        mid = self.crear_membresia().data['id']
        r = self.client.put(f'/api/membresias/{mid}/', {'socio': self.socio.pk, 'plan': self.plan.pk}, format='json')
        self.assertEqual(r.status_code, 405)


class ReglasFijasTests(BaseAPITest):
    def test_plan_siempre_dura_30_dias(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post('/api/planes/', {'nombre': 'Trimestral', 'duracion_dias': 90, 'precio': '90000'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['duracion_dias'], 30)

    def test_clase_dura_una_hora_y_empieza_en_punto(self):
        from clases.models import TipoClase, Sala
        self.client.force_authenticate(self.admin)
        tipo = TipoClase.objects.create(nombre='Spinning')
        sala = Sala.objects.create(nombre='Sala 1', capacidad_maxima=20)
        manana = (self.hoy + timedelta(days=1)).isoformat()
        datos = {'tipo_clase': tipo.pk, 'sala': sala.pk, 'fecha': manana, 'hora_inicio': '07:00',
                 'hora_fin': '09:30', 'cupo_maximo': 10}
        r = self.client.post('/api/sesiones/', datos, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['hora_fin'], '08:00:00')
        # Misma sala y hora: choque de horario.
        self.assertEqual(self.client.post('/api/sesiones/', datos, format='json').status_code, 400)
        # Hora que no es en punto.
        datos['hora_inicio'] = '10:30'
        self.assertEqual(self.client.post('/api/sesiones/', datos, format='json').status_code, 400)

    def test_socios_sin_membresia(self):
        self.crear_membresia()
        otro = Socio.objects.create(rut='11.111.111-1', nombres='Luis', apellidos='Rojas', telefono='+56911111111')
        r = self.client.get('/api/socios/', {'sin_membresia': 'true'})
        ids = [x['id'] for x in r.data['results']]
        self.assertIn(otro.pk, ids)
        self.assertNotIn(self.socio.pk, ids)


class ControlAccesoTests(BaseAPITest):
    def validar(self, codigo):
        return self.client.post('/api/accesos/validar/', {'codigo': codigo}, format='json')

    def test_qr_vigente_permite_y_bloquea_doble_ingreso(self):
        mid = self.crear_membresia().data['id']
        self.pagar(mid)
        token = str(Membresia.objects.get(pk=mid).qr_token)
        self.assertTrue(self.validar(token).data['permitido'])
        self.assertFalse(self.validar(token).data['permitido'])
        self.assertEqual(RegistroAcceso.objects.filter(permitido=True).count(), 1)

    def test_membresia_pendiente_no_permite_ingresar(self):
        mid = self.crear_membresia().data['id']
        token = str(Membresia.objects.get(pk=mid).qr_token)
        self.assertFalse(self.validar(token).data['permitido'])


@override_settings(API_GATEWAY_SECRET='secreto-de-prueba')
class ApiGatewaySecretTests(BaseAPITest):
    def test_sin_cabecera_del_gateway_responde_403(self):
        self.assertEqual(self.client.get('/api/socios/').status_code, 403)

    def test_con_cabecera_del_gateway_funciona(self):
        r = self.client.get('/api/socios/', HTTP_X_GATEWAY_SECRET='secreto-de-prueba')
        self.assertEqual(r.status_code, 200)


class ValidadorRutTests(APITestCase):
    def test_rut_valido_se_normaliza(self):
        self.assertEqual(sanitizar_y_validar_rut('123456785'), '12.345.678-5')

    def test_digito_verificador_incorrecto(self):
        with self.assertRaises(ValidationError):
            sanitizar_y_validar_rut('12.345.678-9')
