import os
from celery import Celery


RABBITMQ_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')

celery_app = Celery(
    'tasks',
    broker=RABBITMQ_URL,
    backend='rpc://',
    include=['workspace.worker'],
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Kyiv',
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

