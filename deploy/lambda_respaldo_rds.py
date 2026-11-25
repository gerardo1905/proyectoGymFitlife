"""
AWS Lambda: snapshot MANUAL de RDS cada 7 horas + aviso por SNS.

RDS no permite respaldos automáticos cada 7 horas (el respaldo automático es
diario + recuperación a un punto en el tiempo). Por eso se programa esta
función con Amazon EventBridge Scheduler:  rate(7 hours)

Configuración (AWS Academy):
  - Runtime: Python 3.12   - Rol de ejecución: LabRole
  - Timeout: 1 minuto
  - Variables de entorno:
        DB_INSTANCE_ID   = fitlife-db
        SNS_TOPIC_ARN    = arn:aws:sns:us-east-1:<cuenta>:fitlife-alertas
        SNAPSHOTS_A_CONSERVAR = 6     (≈ 2 días de snapshots cada 7 h)
"""
import os
from datetime import datetime, timezone

import boto3
from botocore.config import Config

# Tiempos de espera explícitos: la función nunca queda colgada esperando a AWS.
CONFIG_AWS = Config(connect_timeout=5, read_timeout=20, retries={'max_attempts': 3})
rds = boto3.client('rds', config=CONFIG_AWS)
sns = boto3.client('sns', config=CONFIG_AWS)

DB_INSTANCE_ID = os.environ['DB_INSTANCE_ID']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
CONSERVAR = int(os.environ.get('SNAPSHOTS_A_CONSERVAR', '6'))
PREFIJO = f'{DB_INSTANCE_ID}-cada7h-'


def avisar(asunto, mensaje):
    if SNS_TOPIC_ARN:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=asunto[:100], Message=mensaje)


def lambda_handler(event, context):
    marca = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')
    snapshot_id = f'{PREFIJO}{marca}'
    try:
        rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceIdentifier=DB_INSTANCE_ID,
            Tags=[{'Key': 'origen', 'Value': 'lambda-cada-7-horas'}],
        )

        # Rotación: borrar los snapshots más antiguos creados por esta función.
        propios = [
            s for s in rds.describe_db_snapshots(
                DBInstanceIdentifier=DB_INSTANCE_ID, SnapshotType='manual'
            )['DBSnapshots']
            if s['DBSnapshotIdentifier'].startswith(PREFIJO) and s.get('SnapshotCreateTime')
        ]
        propios.sort(key=lambda s: s['SnapshotCreateTime'], reverse=True)
        borrados = []
        for viejo in propios[CONSERVAR:]:
            rds.delete_db_snapshot(DBSnapshotIdentifier=viejo['DBSnapshotIdentifier'])
            borrados.append(viejo['DBSnapshotIdentifier'])

        avisar('FitLife: respaldo RDS iniciado',
               f'Snapshot {snapshot_id} en creación. Eliminados por rotación: {borrados or "ninguno"}.')
        return {'ok': True, 'snapshot': snapshot_id, 'eliminados': borrados}

    except Exception as error:  # se notifica cualquier falla del respaldo
        avisar('FitLife: ERROR en respaldo RDS', f'No se pudo crear {snapshot_id}: {error}')
        raise
