import random

from workspace.celery_cfg import celery_app


@celery_app.task(name="workspace.worker.generate_key_in_range")
def generate_key_in_range(x, y):
    new_key = random.randint(x, y)
    return new_key