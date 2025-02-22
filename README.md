# Dequest
Dequest is a full featured declarative rest client for Python that streamlines the creation of HTTP requests and retrieves the results as DTO. Here is the package's features:

✅ Supports GET, POST, PUT, PATCH and DELETE requests

✅ Optional Caching for GET Requests

✅ Authentication (Static & Dynamic)

✅ Maps API response to DTO object and list (Supports unlimited nested DTOs)

✅ Support query parameters, JSON body and Form-data

✅ Implements Retry & Timeout Handling

✅ Allows Custom Headers per Request (Static & Dynamic)

✅ Circuit Breaker with Custom Fallback Function



## Installation
Run following command to install **dequest** :

```bash
pip install dequest
```

## Usage

Declare a function with `@sync_client` decorator and pass the `dto_class` parameter to map the response to a DTO. You can also pass the `method`, `timeout`, `retries`, `retry_delay`, `auth_token`, `api_key`, `default_headers`, and `enable_cache` parameters.

```python
from dequest.clients import sync_client

class UserDto:
    name: str
    address: AddressDto
    friends: list[str]

    def __init__(self, name, address, friends):
        self.name = name
        self.address = address
        self.friends = friends


@sync_client(dto_class=UserDto)
def get_user(user_id):
    return {
        "url": f"https://jsonplaceholder.typicode.com/users/{user_id}",
    }

user = get_user(1)
```

Retrieving a list of users by city name using query parameters:

```python
@sync_client(dto_class=UserDto)
def get_users(city_name) -> List[UserDto]:
    return {
        "url": f"https://jsonplaceholder.typicode.com/users/",
        "params": {"city": city_name},  # Query parameter to filter by city name
    }

users = get_users("Paris")
```

### Cache

To enable caching, set the `enable_cache` parameter to `True` in the `sync_client` decorator. You can also pass the `cache_ttl` parameter to set the cache expiration time in seconds, the default value is None which means no expiration. Dequest supports `redis` and `in_memory` cache drivers, wich can be configured in `dequest.config.DequestConfig` which is a static class. The default cache provider is `in_memory`.

```python
from dequest.clients import sync_client
from dequest.config import DequestConfig

DequestConfig.cache_driver = "redis"

@sync_client(dto_class=UserDto, enable_cache=True, cache_ttl=300)
def get_user(user_id):
    return {
        "url": f"https://jsonplaceholder.typicode.com/users/{user_id}",
    }

user = get_user(1)
```

### Authentication

To add authentication, pass the `auth_token` parameter to the `sync_client` decorator. You can also pass the `api_key` parameter to add an API key to the request headers.

Static authentication:

```python
from dequest.clients import sync_client

@sync_client(dto_class=UserDto, auth_token="my_auth_token")
def get_user(user_id) -> UserDto:
    return {
        "url": f"https://jsonplaceholder.typicode.com/users/{user_id}",
    }

user = get_user(1)
```

Dynamic authentication token generation:

```python
from dequest.clients import sync_client

def get_auth_token():
    return "my_auth_token"

@sync_client(dto_class=UserDto, auth_token=get_auth_token)
def get_user(user_id):
    return {
        "url": f"https://jsonplaceholder.typicode.com/users/{user_id}",
    }
```

## License

Dequest is released under the [BSD 3-Clause License](https://opensource.org/licenses/BSD-3-Clause).