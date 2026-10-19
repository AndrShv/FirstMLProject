import logging

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from workspace.configs.celery_cfg import celery_app
from workspace.configs.db_config import get_db
from workspace.dto.ai_requests import GeneratingRequest
from workspace.repo import output_repo
from workspace.services.evaluate_data import evaluate
from workspace.services.worker import generating_method
generator_router = APIRouter()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@generator_router.post("/generate")
def generate_text(data: GeneratingRequest):
    logger.info(f"Generating text for prompt: {data.prompt}")

    new_task = generating_method.delay(data.prompt, data.max_new_tokens)


    logger.info(f"Task dispatched with ID: {new_task.id}")
    return {
        "status": "queued",
        "prompt": data.prompt,
        "task_id": new_task.id,
        "detail": "Task has been accepted for processing by Celery worker.",
    }


@generator_router.post("/stats")
async def get_stats(session: AsyncSession = Depends(get_db)):
    logger.info(f"Generating stats for requests")
    output_statistics = await output_repo.OutputRepository(session).get_stats()
    return output_statistics

@generator_router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    logger.info(f"Getting status for task: {task_id}")
    task_result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

@generator_router.get("/asses")
@generator_router.get("/assesment")
async def asses_ai():
    logger.info("Starting dataset assessment")
    return await evaluate()
