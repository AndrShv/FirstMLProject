import asyncio
import hashlib
import logging
from datetime import timezone, datetime
from workspace.configs.celery_cfg import celery_app
from workspace.configs.db_config import _get_session_factory
from workspace.configs.settings import settings
from workspace.entity.db_models import DbOutputs
from workspace.helpers.time_logger import count_latency
from workspace.repo import output_repo
from workspace.services.ai_cache_service import AiCacheService
from workspace.services.ai_service import generate_text
from workspace.entity.redis_models import AiCache
from redis.asyncio import Redis

redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
cache_service = AiCacheService(redis_client)
logger = logging.getLogger(__name__)

async def save_output_to_db(prompt: str, response_text: str, api_result: dict, cache_hit: bool):
    async with _get_session_factory() as session:
         saved_output = DbOutputs(
             timestamp=datetime.now(timezone.utc),
             prompt=prompt,
             response=response_text,
             latency=api_result.get("latency", 0.0),
             input_tokens=api_result["input_tokens"],
             output_tokens=api_result["output_tokens"],
             cache_hit=cache_hit
            )
    await output_repo.OutputRepository.save_output(saved_output)


async def process_generation_with_cache(prompt: str, max_new_tokens: int) -> str:
    logger.info(f"Processing generation for prompt: {prompt}")
    hashed_prompt = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:10]
    logger.info(f"Processing generation for prompt: {hashed_prompt}")
    cached_obj = await cache_service.get_cached_data(prompt)
    if cached_obj:
        logger.info(f"Cache hit for prompt: {prompt}")
        return cached_obj.response

    api_result = generate_text(prompt, max_new_tokens)
    response_text = api_result["response"]

    logger.info(f"Processing generation for prompt: {prompt}")

    cache_payload = AiCache(
        request_key=hashed_prompt,
        request=prompt,
        response=response_text,
        input_tokens=api_result["input_tokens"],
        output_tokens=api_result["output_tokens"]
    )



    logger.info(f"Saving output to DB for prompt: {prompt}")
    await save_output_to_db(prompt, response_text, api_result, cache_hit=True)
    await cache_service.save_data(prompt, cache_payload)
    logger.info(f"Saving output to DB for prompt: {prompt}")
    return response_text


@count_latency
@celery_app.task(name="workspace.worker.generating_method")
def generating_method(prompt: str, max_new_tokens: int = 100):
    return asyncio.run(process_generation_with_cache(prompt, max_new_tokens))