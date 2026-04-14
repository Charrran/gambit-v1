import redis

from app.core.config import settings


redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
