import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# In-memory fallback cache when Redis is not running or during standalone unit tests
class InMemoryCache:
    def __init__(self):
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}

    def _cleanup_expired(self):
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp and exp <= now]
        for k in expired:
            self._store.pop(k, None)

    async def get(self, key: str) -> Optional[str]:
        self._cleanup_expired()
        item = self._store.get(key)
        if item is None:
            return None
        val, exp = item
        if exp and exp <= time.time():
            self._store.pop(key, None)
            return None
        return val

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        expire_at = (time.time() + ex) if ex else None
        self._store[key] = (value, expire_at)
        return True

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def incr(self, key: str) -> int:
        self._cleanup_expired()
        val = await self.get(key)
        if val is None:
            new_val = 1
        else:
            try:
                new_val = int(val) + 1
            except ValueError:
                new_val = 1
        item = self._store.get(key)
        exp = item[1] if item else None
        self._store[key] = (str(new_val), exp)
        return new_val

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._store:
            val, _ = self._store[key]
            self._store[key] = (val, time.time() + seconds)
            return True
        return False

    async def flush(self):
        self._store.clear()

    async def ping(self) -> bool:
        return True


class RedisManager:
    _instance: Optional["RedisManager"] = None

    def __init__(self):
        self._redis_client = None
        self._fallback_cache = InMemoryCache()
        self._using_fallback = False

    @classmethod
    def get_instance(cls) -> "RedisManager":
        if cls._instance is None:
            cls._instance = RedisManager()
        return cls._instance

    async def get_client(self):
        if self._using_fallback:
            return self._fallback_cache

        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis
                from app.core.config import settings

                url = settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
                if settings.REDIS_PASSWORD:
                    url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
                
                client = aioredis.from_url(url, decode_responses=True, socket_timeout=1.5, socket_connect_timeout=1.5)
                # Test connection
                await client.ping()
                self._redis_client = client
                logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                return self._redis_client
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}). Falling back to in-memory cache/rate limiter.")
                self._using_fallback = True
                return self._fallback_cache
        return self._redis_client

    async def get(self, key: str) -> Optional[str]:
        client = await self.get_client()
        try:
            return await client.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}. Using fallback.")
            return await self._fallback_cache.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        client = await self.get_client()
        try:
            return await client.set(key, value, ex=ex)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}. Using fallback.")
            return await self._fallback_cache.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        client = await self.get_client()
        try:
            return await client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}. Using fallback.")
            return await self._fallback_cache.delete(key)

    async def get_json(self, key: str) -> Optional[Any]:
        val = await self.get(key)
        if val is not None:
            try:
                return json.loads(val)
            except Exception:
                return None
        return None

    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        serialized = json.dumps(value)
        return await self.set(key, serialized, ex=ex)

    async def revoke_token(self, jti: str, expire_seconds: int = 86400) -> bool:
        key = f"revoked_token:{jti}"
        return await self.set(key, "1", ex=expire_seconds)

    async def is_token_revoked(self, jti: str) -> bool:
        key = f"revoked_token:{jti}"
        res = await self.get(key)
        return res is not None

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        """
        Check and increment rate limit for a key using fixed window.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        client = await self.get_client()
        rate_key = f"ratelimit:{key}"
        try:
            current = await client.incr(rate_key)
            if current == 1:
                await client.expire(rate_key, window_seconds)
            
            if current > max_requests:
                return False, 0, window_seconds
            return True, max_requests - current, 0
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}. Using fallback.")
            current = await self._fallback_cache.incr(rate_key)
            if current == 1:
                await self._fallback_cache.expire(rate_key, window_seconds)
            if current > max_requests:
                return False, 0, window_seconds
            return True, max_requests - current, 0

    async def close(self):
        if self._redis_client is not None and not self._using_fallback:
            try:
                await self._redis_client.close()
            except Exception:
                pass
            self._redis_client = None


redis_manager = RedisManager.get_instance()
