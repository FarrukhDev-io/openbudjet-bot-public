import os
import uuid
import logging
import asyncio
import redis.asyncio as aioredis
from typing import Optional

logger = logging.getLogger("redis_client")

# Load environment variable
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_pool: Optional[aioredis.ConnectionPool] = None


async def init_redis() -> aioredis.ConnectionPool:
    """Initialize Redis connection pool"""
    global redis_pool
    if redis_pool is None:
        # FIX (Roast R4): Resilient Redis connection pool for horizontal autoscaling
        redis_pool = aioredis.ConnectionPool.from_url(
            REDIS_URL, 
            decode_responses=True,
            max_connections=50,
            socket_timeout=5.0
        )
    return redis_pool


async def get_redis_client() -> aioredis.Redis:
    """Acquire Redis client instance from the pool"""
    if redis_pool is None:
        await init_redis()
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """Gracefully close Redis pool"""
    global redis_pool
    if redis_pool is not None:
        await redis_pool.disconnect()
        redis_pool = None


class RedisDistributedLock:
    """
    FIX (Roast R4): Redis Distributed Lock (Redlock pattern)
    Ensures key-based mutual exclusion across multiple stateless microservices.
    """
    def __init__(self, key: str, lease_time_ms: int = 10000, acquire_timeout_s: float = 5.0):
        self.key = f"lock:{key}"
        self.lease_time_ms = lease_time_ms
        self.acquire_timeout_s = acquire_timeout_s
        self.lock_value = str(uuid.uuid4())
        self.redis: Optional[aioredis.Redis] = None

    async def __aenter__(self):
        self.redis = await get_redis_client()
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < self.acquire_timeout_s:
            # Set key if not exists (nx=True) with milliseconds expiry (px)
            acquired = await self.redis.set(
                self.key, self.lock_value, px=self.lease_time_ms, nx=True
            )
            if acquired:
                return self
            await asyncio.sleep(0.05)
        raise TimeoutError(f"Could not acquire Redis lock for key: {self.key}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Atomic release using Lua Script to prevent releasing locks owned by other processes
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            if self.redis:
                await self.redis.eval(release_script, 1, self.key, self.lock_value)
        except Exception as e:
            logger.exception("Failed to release Redis lock: %s", e)
        finally:
            if self.redis:
                await self.redis.close()
