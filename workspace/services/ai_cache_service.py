from uuid import UUID

from redis import RedisError
from redis.asyncio import Redis
import logging

from workspace.entity.redis_models import AiCache

logger = logging.getLogger(__name__)


class AiCacheService:
    def __init__(self, redis_client: Redis):
        self.cache = redis_client

    def build_key(self, user_id: UUID) -> str:
        return f"ai_cache:{user_id}"


    async def get_cached_data(self, user_id: UUID) -> AiCache | None:
        logger.info(f"Fetching from Redis: {user_id}")
        key = self.build_key(user_id)
        try:
            cached_data = await self.cache.get(key)
            if not cached_data:
                logger.info(f"No cached data found for user_id={user_id}")
                return None
            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode("utf-8")
            logger.info(f"Cache HIT for user_id={user_id}")
            return AiCache.model_validate_json(cached_data)

        except RedisError as e:
            logger.warning(f"Failed to fetch from Redis: {e}. Falling back to API.")
            return None


    async def saved_data(self, user_id: UUID, data: AiCache):
        key = self.build_key(user_id)

        try:
            await self.cache.set(
                key,
                data.model_dump_json(by_alias=True),
                ex=1800
            )
            logger.info(f"Data cached for user_id={user_id}")
        except RedisError as e:
            logger.warning(f"Failed to save to Redis cache: {e}")

    async def delete_cached_data(self, user_id: UUID):
        key = self.build_key(user_id)
        try:
            await self.cache.delete(key)
            logger.info(f"Data cache deleted for user_id={user_id}")
        except RedisError as e:
            logger.warning(f"Failed to delete from Redis cache: {e}")

