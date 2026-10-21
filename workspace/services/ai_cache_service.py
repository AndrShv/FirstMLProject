import hashlib
import logging
from redis import RedisError
from redis.asyncio import Redis

from workspace.entity.redis_models import AiCache

logger = logging.getLogger(__name__)


class AiCacheService:
    def __init__(self, redis_client: Redis):
        self.cache = redis_client

    def build_key(self, prompt: str) -> str:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return f"ai_cache:{prompt_hash}"

    async def get_cached_data(self, prompt: str) -> AiCache | None:
        key = self.build_key(prompt)
        logger.info(f"Fetching from Redis with key: {key}")
        try:
            cached_data = await self.cache.get(key)
            if not cached_data:
                logger.info("Cache MISS for prompt")
                return None

            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode("utf-8")

            logger.info("Cache HIT for prompt!")
            return AiCache.model_validate_json(cached_data)

        except RedisError as e:
            logger.warning(f"Failed to fetch from Redis: {e}. Falling back to API.")
            return None

    async def save_data(self, prompt: str, data: AiCache):
        key = self.build_key(prompt)
        try:
            await self.cache.set(
                key,
                data.model_dump_json(by_alias=True),
                ex=1800
            )
            logger.info("Data cached successfully for prompt")
        except RedisError as e:
            logger.warning(f"Failed to save to Redis cache: {e}")

    async def delete_cached_data(self, prompt: str):
        key = self.build_key(prompt)
        try:
            await self.cache.delete(key)
            logger.info("Data cache deleted for prompt")
        except RedisError as e:
            logger.warning(f"Failed to delete from Redis cache: {e}")