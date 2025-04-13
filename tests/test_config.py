from dequest import DequestConfig


def test_get_config():
    expected_port = 6379
    expected_redis_db = 0
    DequestConfig.config(
        CACHE_PROVIDER="redis",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0,
        REDIS_PASSWORD=None,
        REDIS_SSL=False,
    )

    assert DequestConfig.CACHE_PROVIDER == "redis"
    assert DequestConfig.REDIS_HOST == "localhost"
    assert expected_port == DequestConfig.REDIS_PORT
    assert expected_redis_db == DequestConfig.REDIS_DB
    assert DequestConfig.REDIS_PASSWORD is None
    assert DequestConfig.REDIS_SSL is False
