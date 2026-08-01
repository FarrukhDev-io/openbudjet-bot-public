import time
import logging
from redis_client import get_redis_client

logger = logging.getLogger("rate_limiter")


async def is_rate_limited(key: str, max_requests: int = 3, window_seconds: int = 600) -> bool:
    """
    FIX (Roast R4): Redis-based Distributed Sliding Window Rate Limiter.
    Returns True if user has exceeded max_requests within window_seconds, False otherwise.
    Falls back to False (not limited) if Redis is down to preserve availability.
    """
    try:
        redis = await get_redis_client()
        now = time.time()
        redis_key = f"rate_limit:{key}"
        
        # Sliding window implementation using Sorted Sets
        async with redis.pipeline(transaction=True) as pipe:
            # 1. Remove timestamps older than current window
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            # 2. Get current number of requests in the window
            pipe.zcard(redis_key)
            # 3. Add current request timestamp
            pipe.zadd(redis_key, {str(now): now})
            # 4. Set expiry on key to save memory
            pipe.expire(redis_key, window_seconds)
            
            results = await pipe.execute()
            
        requests_count = results[1]
        
        if requests_count >= max_requests:
            # Over the limit: roll back the added timestamp to prevent bloat
            await redis.zrem(redis_key, str(now))
            return True
            
        return False
    except Exception as e:
        logger.exception("Redis rate limiter connection failed. Falling back to permit request: %s", e)
        return False
