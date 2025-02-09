import logging

import redis

from ...config import DequestConfig

logger = logging.getLogger(__name__)
logger.setLevel(DequestConfig.get_log_level())


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
        return self.client.get(key)
