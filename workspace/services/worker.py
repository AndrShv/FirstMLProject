import asyncio
import hashlib

from google.protobuf import timestamp

from workspace.configs.celery_cfg import celery_app
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


async def save_output_to_db(prompt: str, response_text: str, api_result: dict, cache_hit: bool):
    saved_output = DbOutputs(
        timestamp=timestamp.Timestamp().GetCurrentTime(),
        prompt=prompt,
        response=response_text,
        latency=api_result["latency"],
        input_tokens=api_result["input_tokens"],
        output_tokens=api_result["output_tokens"],
        cache_hit=cache_hit
    )
    await output_repo.OutputRepository.save_output(saved_output)


async def process_generation_with_cache(prompt: str, max_new_tokens: int) -> str:
    hashed_prompt = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:10]
    cached_obj = await cache_service.get_cached_data(prompt)
    if cached_obj:
        return cached_obj.response

    api_result = generate_text(prompt, max_new_tokens)
    response_text = api_result["response"]

    cache_payload = AiCache(
        request_key=hashed_prompt,
        request=prompt,
        response=response_text,
        input_tokens=api_result["input_tokens"],
        output_tokens=api_result["output_tokens"]
    )


    await save_output_to_db(prompt, response_text, api_result, cache_hit=True)
    await cache_service.save_data(prompt, cache_payload)

    return response_text


@count_latency
@celery_app.task(name="workspace.worker.generating_method")
def generating_method(prompt: str, max_new_tokens: int = 100):
    return asyncio.run(process_generation_with_cache(prompt, max_new_tokens))