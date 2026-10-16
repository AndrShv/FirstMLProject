import logging

from celery.result import AsyncResult
from fastapi import APIRouter
from workspace.celery_cfg import celery_app
from workspace.worker import generating_method
generator_router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@generator_router.get("/")
def read_root():
    logger.info("Health check endpoint called.")
    return {"status": "ok", "message": "FastAPI is running successfully!"}


@generator_router.post("/generate")
def generate_text(prompt: str, max_new_tokens: int = 500):
    logger.info(f"Generating text for prompt: {prompt}")

    new_task = generating_method.delay(prompt, max_new_tokens)


    logger.info(f"Task dispatched with ID: {new_task.id}")
    return {
        "status": "queued",
        "prompt": prompt,
        "task_id": new_task.id,
        "detail": "Task has been accepted for processing by Celery worker.",
    }


@generator_router.get("/task_status/{task_id}")
def get_task_status(task_id: str):
    logger.info(f"Checking status for task ID: {task_id}")
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.failed():
        return {
            "status": "failed",
            "result": str(task_result.result),
            "task_id": task_id
        }

    if task_result.ready():
        return {
            "status": "completed",
            "result": task_result.get(),
            "task_id": task_id
        }
    else:
        logger.info(f"Task {task_id} is still processing.")
        return {
            "task_id": task_id,
            "status": "Pending",
            "result": None
        }
