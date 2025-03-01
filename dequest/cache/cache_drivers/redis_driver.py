import redis

from dequest.utils import get_logger

logger = get_logger()


class RedisDriver:
    def __init__(
        self,
        host,
        port=6379,
        decode_responses=True,
        db=0,
        password=None,
        ssl=False,
    ):
        self.client = redis.StrictRedis(
            host=host,
            port=port,
            decode_responses=decode_responses,
            db=db,
            password=password,
            ssl=ssl,
        )
        logger.info("Redis client initialized")

    def expire_key(self, key, seconds):
        return self.client.expire(key, seconds)

    def set_key(self, key, value, expire=None):
        self.client.set(key, value, ex=expire)

    def get_key(self, key):
        value = self.client.get(key)
        if value is not None:
            logger.info("Cache hit for key: %s", key)
            return value

        return None

    def clear(self):
        self.client.flushdb()
