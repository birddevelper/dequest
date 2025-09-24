# Dequest
[![PyPI - Version](https://img.shields.io/pypi/v/dequest.svg?style=for-the-badge)](https://pypi.org/project/dequest/)
![Pre Commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge)
![Code Style - Ruff](https://img.shields.io/badge/code%20style-ruff-30173D.svg?style=for-the-badge)

Dequest is a full featured declarative HTTP client for Python that simplifies the creation and sending HTTP requests and retrieves the results as DTO.

## Why dequest?

* **Fast to code:**
  Develop API-integrated features **2–3× faster** with zero boilerplate—just decorate and go.

* **No boilerplate:**
  Say goodbye to manual `requests`, `asyncio`, retries, and JSON parsing. One function = one clean API call.

* **Safe and typed:**
  Supports Pydantic-style DTOs, typed parameters, and response mapping—minimizing runtime surprises.

* **Resilient by default:**
  Built-in support for **retries**, **caching**, and **circuit breakers**. Your APIs won’t bring your app down.

* **Declarative and elegant:**
  Define path, query, form, and body parameters cleanly with `PathParameter`, `QueryParameter`, `JsonBody`, etc.

* **Smart caching:**
  Add in-memory or Redis-based caching with a single flag.

* **Async without async:**
  Use `@async_client` and fire off non-blocking API calls without dealing with asyncio yourself.

* **Built-in callbacks & fallbacks:**
  Handle async responses or fallback gracefully when APIs are flaky, dequest makes it smooth.

* **Framework-agnostic:**
  Works in **any Python project**, from CLI apps to FastAPI, Flask, Django, and beyond.


## Key Features
✅ Supports GET, POST, PUT, PATCH and DELETE requests

✅ Sync & Async Client

✅ Optional Caching for GET Requests (Support In-Memory, Redis, Django Cache)

✅ Support authentication (Static & Dynamic)

✅ Maps API Json/XML response to DTO object and list (Supports unlimited nested DTOs)

✅ Support query parameters, JSON body and Form-data

✅ Retry and Backoff

✅ Allows Custom Headers per Request (Static & Dynamic)

✅ Circuit Breaker with Custom Fallback Function

✅ API parameter mapping and type checking

✅ Logging

## Installation
To install Dequest, simply run:

```sh
pip install dequest
```

## Getting Started

## Configuration
Dequest allows global configuration via `DequestConfig`, the configuration can be set using `.config` method of the `DequestConfig` class:

```python
from dequest import DequestConfig

DequestConfig.config(
    cache_provider="redis", # defaults to "in_memory"
    redis_host="my-redis-server.com",
    redis_port=6380,
    redis_db=1,
    redis_password="securepassword",
    redis_ssl=True,
)
```

### Synchronous API Calls
Use `@sync_client` to make synchronous HTTP requests without writing boilerplate code:

```python
from dequest import sync_client, QueryParameter
from typing import List
from dataclasses import dataclass

@dataclass
class UserDto:
    id: int
    name: str
    city: str


@sync_client(url="https://jsonplaceholder.typicode.com/users", dto_class=UserDto)
def get_users(city: QueryParameter[str, "city_name"]) -> List[UserDto]:
    pass

users = get_users(city="New York")
print(users)
```

### Asynchronous API Calls
Use `@async_client` to make non-blocking HTTP requests:

```python
from dequest import async_client, HTTPMethod

async def callback_function(response):
    print(response)

@async_client(url="https://api.example.com/notify", method=HTTPMethod.POST, callback=callback_function)
def notify():
    pass

notify()
```

## Handling Parameters
### Path Parameters
Pass values inside the URL using `PathParameter`:

```python
from dequest import sync_client, PathParameter

@sync_client(url="https://jsonplaceholder.typicode.com/users/{user_id}", dto_class=UserDto)
def get_user(user_id: PathParameter[int]) -> UserDto:
    pass

user = get_user(user_id=1)
print(user)
```

### Query Parameters
Pass values as URL query parameters using `QueryParameter`:

```python
from dequest import sync_client, QueryParameter

@sync_client(url="https://api.example.com/search", dto_class=UserDto)
def search_users(name: QueryParameter[str]):
    pass

users = search_users(name="Alice")
```

### JSON Parameters
For POST requests pass values as JSON payload using `JsonBody`:

```python
from dequest import sync_client, HTTPMethod, JsonBody

@sync_client(url="https://api.example.com/users", method=HTTPMethod.POST, dto_class=UserDto)
def create_user(name: JsonBody, city: JsonBody) -> UserDto:
    pass

new_user = create_user(name="Alice", city="Berlin")
```

## Advanced Features
### Retries
Automatically retry failed requests on specified exceptions:

```python
@sync_client(url="https://api.example.com/data", retries=3, retry_on_exceptions=(ConnectionError, HTTPError), retry_delay=2)
def get_data():
    pass
```

### Caching
Enable caching for GET requests:

```python
@sync_client(url="https://api.example.com/popular-posts", enable_cache=True, cache_ttl=60)
def get_popular_posts():
    pass
```

### Circuit Breaker
Prevent excessive calls to failing APIs using a circuit breaker:

```python
from dequest import sync_client, CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

@sync_client(url="https://api.unstable.com/data", circuit_breaker=breaker)
def get_unstable_data():
    pass
```

### Fallback on Failure
Define a fallback function for when the circuit breaker is open:

```python
from dequest import CircuitBreaker

def fallback_response():
    return {"message": "Service unavailable, returning cached data"}

breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10, fallback_function=fallback_response)

@sync_client(url="https://api.unstable.com/data", circuit_breaker=breaker)
def fetch_unstable_data():
    pass
```

## Documentation

For comprehensive details on Dequest, please refer to the full documentation available at [Read the Docs](https://dequest-documentation.readthedocs.io/en/latest/).

## License

Dequest is released under the [BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause).
