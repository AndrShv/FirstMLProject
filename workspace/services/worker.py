
from workspace.configs.celery_cfg import celery_app
from workspace.services.ai_service import generate_text


@celery_app.task(name="workspace.worker.generating_method")
def generating_method(prompt: str, max_new_tokens: int = 100):
    new_key = generate_text(prompt, max_new_tokens)
    return new_key