import asyncio
import hashlib
import logging
from datetime import timezone, datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from workspace.configs.celery_cfg import celery_app
from workspace.configs.settings import settings
from workspace.entity.db_models import DbOutputs
from workspace.helpers.time_logger import count_latency
from workspace.repo import output_repo
from workspace.services.ai_cache_service import AiCacheService
from workspace.services.ai_service import generate_text
from workspace.entity.redis_models import AiCache
from redis.asyncio import Redis
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=False,
    socket_connect_timeout=5,
    socket_timeout=5,
)
cache_service = AiCacheService(redis_client)
logger = logging.getLogger(__name__)


async def save_output_to_db(prompt: str, response_text: str, api_result: dict, cache_hit: bool):
    engine = create_async_engine(settings.database_url, connect_args={"statement_cache_size": 0})
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = output_repo.OutputRepository(session)
        saved_output = DbOutputs(
            timestamp=datetime.now(timezone.utc),
            prompt=prompt,
            response=response_text,
            latency=api_result.get("latency", 0.0),
            input_tokens=api_result.get("input_tokens", 0),
            output_tokens=api_result.get("output_tokens", 0),
            cache_hit=cache_hit
        )
        await repo.save_output(saved_output)
    await engine.dispose()


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
    await save_output_to_db(prompt, response_text, api_result, cache_hit=False)
    await cache_service.save_data(prompt, cache_payload)
    logger.info(f"Saving output to DB for prompt: {prompt}")
    return response_text


@celery_app.task(name="workspace.worker.generating_method", bind=True)
@count_latency
def generating_method(self, prompt: str, max_new_tokens: int = 100):
    try:
        return asyncio.run(process_generation_with_cache(prompt, max_new_tokens))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
