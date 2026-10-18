from celery import Celery

from workspace.configs.settings import Settings
celery_app = Celery(
    'tasks',
    broker=Settings.RABBITMQ_URL,
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

