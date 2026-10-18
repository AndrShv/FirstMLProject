import logging
from workspace.repo import output_repo
from workspace.services.worker import generating_method
from fastapi import APIRouter
generator_router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


@generator_router.post("/stats")
def get_stats():
    logger.info(f"Generating stats for requests")
    output_statistics = output_repo.OutputRepository.get_stats()
    return output_statistics

