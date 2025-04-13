from dequest import cache


def test_singletone_cache():
    cache1 = cache.get_cache()
    cache2 = cache.get_cache()

    assert cache1 is cache2
