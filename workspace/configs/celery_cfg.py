from celery import Celery

from workspace.configs.settings import settings
celery_app = Celery(
    'tasks',
    broker=settings.rabbitmq_url, # broker URL for RabbitMQ
    backend=settings.celery_result_backend, # results from AI in Redis
    include=['workspace.services.worker'],
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

