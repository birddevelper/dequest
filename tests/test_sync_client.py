import datetime
import http
import json
import time
import urllib

import pytest
import respx
from httpx import HTTPError, Response

from dequest import ConsumerType, FormParameter, JsonBody, PathParameter, sync_client
from dequest.circuit_breaker import CircuitBreaker, CircuitBreakerState
from dequest.exceptions import DequestError, InvalidParameterValueError


class UserDTO:
    name: str
    grade: int
    city: str
    birthday: datetime.date

    def __init__(self, name, grade, city, birthday):
        self.name = name
        self.grade = int(grade) if grade else grade
        self.city = city
        self.birthday = datetime.date.fromisoformat(birthday) if birthday else None


@respx.mock
def test_sync_client():
    data = {"name": "Alice", "grade": 14, "city": "New York", "birthday": "2000-01-01"}
    route = respx.get("https://api.example.com/users/1").mock(
        return_value=Response(200, json=data),
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)
    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])
    assert route.call_count == 1


@respx.mock
def test_sync_client_with_source_field():
    data = {
        "position": "Developer",
        "user": {
            "name": "Alice",
            "grade": 14,
            "city": "New York",
            "birthday": "2000-01-01",
        },
    }
    respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        source_field="user",
    )
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == data["user"]["name"]
    assert user.grade == data["user"]["grade"]
    assert user.city == data["user"]["city"]
    assert user.birthday == datetime.date.fromisoformat(data["user"]["birthday"])


@respx.mock
def test_sync_client_with_headers():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        headers={"X-Test-Header": "test"},
    )
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])
    assert api.calls[0].request.headers["X-Test-Header"] == "test"


@respx.mock
def test_sync_client_retry():
    expected_number_of_calls = 4  # 1st call + 3 retries
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=3,
        retry_on_exceptions=(HTTPError,),
    )
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(DequestError):
        get_user(1)

    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_retry__generator():
    def delay_gen():
        yield 1
        yield 2
        yield 3

    expected_number_of_calls = 4
    expected_total_delay = 6  # 1 + 2 + 3 seconds
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=3,
        retry_delay=delay_gen,
        retry_on_exceptions=(HTTPError,),
    )
    def get_user(user_id: PathParameter[int]):
        pass

    start_time = time.time()
    with pytest.raises(DequestError):
        get_user(1)
    elapsed_time = time.time() - start_time

    assert elapsed_time >= expected_total_delay
    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_retry__iterator():
    def delay_gen():
        return iter([1, 2, 3])

    expected_number_of_calls = 4
    expected_total_delay = 6  # 1 + 2 + 3 seconds
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=3,
        retry_delay=delay_gen,
        retry_on_exceptions=(HTTPError,),
    )
    def get_user(user_id: PathParameter[int]):
        pass

    start_time = time.time()
    with pytest.raises(DequestError):
        get_user(1)
    elapsed_time = time.time() - start_time

    assert elapsed_time >= expected_total_delay
    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_no_retry():
    expected_number_of_calls = 1
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(DequestError):
        get_user(1)

    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_retry__giveup_not_meet():
    expected_number_of_calls = 4  # 1st call + 3 retries
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=3,
        retry_on_exceptions=(HTTPError,),
        giveup=lambda e: e.response.status_code == http.HTTPStatus.NOT_FOUND,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(DequestError):
        get_user(1)

    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_retry__giveup_meet():
    expected_number_of_calls = 1
    api = respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json={"message": "Internal Server Error"},
            status_code=500,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=3,
        retry_on_exceptions=(HTTPError,),
        giveup=lambda e: e.response.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(DequestError):
        get_user(1)

    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_with_cache():
    expected_number_of_calls = 1
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = respx.get(
        "https://api.example.com/users/4",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        enable_cache=True,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    for _ in range(4):
        user = get_user(4)

        assert user.name == data["name"]
        assert user.grade == data["grade"]
        assert user.city == data["city"]

        assert user.birthday == datetime.date.fromisoformat(data["birthday"])

    assert api.call_count == expected_number_of_calls


@respx.mock
def test_sync_client_no_dto_class():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    respx.get(
        "https://api.example.com/users/6",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(url="https://api.example.com/users/{user_id}")
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(user_id=6)

    assert user["name"] == data["name"]
    assert user["grade"] == data["grade"]
    assert user["city"] == data["city"]
    assert user["birthday"] == data["birthday"]


@respx.mock
def test_sync_client_with_headers_and_auth():
    data = {"name": "Alice", "grade": 14, "city": "New York", "birthday": "2000-01-01"}
    route = respx.get("https://api.example.com/users/1").mock(
        return_value=Response(200, json=data),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        headers={"X-Test-Header": "test"},
        auth_token="my_auth_token",  # noqa: S106
    )
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(user_id=1)

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])
    assert route.calls[0].request.headers["X-Test-Header"] == "test"
    assert route.calls[0].request.headers["Authorization"] == "Bearer my_auth_token"


@respx.mock
def test_sync_client_post_method_with_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }

    route = respx.post("https://api.example.com/users").mock(
        return_value=Response(200, json=data),
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(
        name: FormParameter[str],
        grade: FormParameter[int],
        city: FormParameter[str],
        birthday: FormParameter[str],
    ):
        pass

    save_user(name="Alice", grade=14, city="New York", birthday="2000-01-01")

    assert route.calls[0].request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert b"name=Alice" in route.calls[0].request.content


@respx.mock
def test_sync_client_post_method_with_json_payload():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }

    # Mock the POST request to the API
    route = respx.post("https://api.example.com/users").mock(
        return_value=Response(
            status_code=200,
            json={
                "name": data["name"],
                "grade": data["grade"],
                "city": data["city"],
                "birthday": data["birthday"],
            },
        ),
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(
        name: JsonBody,
        grade: JsonBody,
        city_name: JsonBody["city"],  # noqa: F821
        birthday: JsonBody,
    ):
        pass

    save_user(name="Alice", grade=14, city_name="New York", birthday="2000-01-01")

    request = route.calls[0].request
    body_json = json.loads(request.content.decode())

    assert request.headers["Content-Type"] == "application/json"
    assert body_json == {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }


@pytest.mark.parametrize(
    ("client_calls", "cb_is_open"),
    [
        (1, CircuitBreakerState.CLOSED),
        (2, CircuitBreakerState.CLOSED),
        (3, CircuitBreakerState.OPEN),
    ],
)
@respx.mock
def test_sync_client_circute_breaker(client_calls, cb_is_open):
    circut_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    client_retries = 2

    # Mock the GET request returning 500
    route = respx.get("https://api.example.com/users/1").mock(
        return_value=Response(
            status_code=500,
            json={"message": "Internal Server Error"},
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=client_retries,
        retry_on_exceptions=(HTTPError,),
        circuit_breaker=circut_breaker,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    for _ in range(client_calls):
        with pytest.raises(DequestError):
            get_user(user_id=1)

    assert circut_breaker.get_state() == cb_is_open
    assert route.call_count == client_calls * (client_retries + 1)


@respx.mock
def test_sync_client_circute_breaker__recovery():
    circut_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    expected_number_of_calls = 1

    route = respx.get("https://api.example.com/users/1").mock(
        return_value=Response(status_code=200, json={"message": "OK"}),
    )
    circut_breaker.state = CircuitBreakerState.OPEN
    circut_breaker.last_failure_time = time.time() - 60  # one minute ago

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        circuit_breaker=circut_breaker,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    result = get_user(user_id=1)

    assert circut_breaker.get_state() == CircuitBreakerState.CLOSED
    assert route.call_count == expected_number_of_calls
    assert result == {"message": "OK"}


@respx.mock
def test_sync_client_circute_breaker__fallback():
    def fallback_response(user_id):
        return {"message": "Service temporarily unavailable, please try later."}

    circut_breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=30,
        fallback_function=fallback_response,
    )
    expected_number_of_calls = 0

    route = respx.get("https://api.example.com/users/1").mock(
        return_value=Response(
            status_code=500,
            json={"message": "Internal Server Error"},
        ),
    )
    circut_breaker.state = CircuitBreakerState.OPEN
    circut_breaker.last_failure_time = time.time()

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        circuit_breaker=circut_breaker,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    result = get_user(user_id=1)

    assert circut_breaker.get_state() == CircuitBreakerState.OPEN
    assert route.call_count == expected_number_of_calls
    assert result == {"message": "Service temporarily unavailable, please try later."}


@respx.mock
def test_sync_client_xml_response():
    data = "<student><name>Alice</name><grade>14</grade><city>New York</city><birthday>2000-01-01</birthday></student>"
    expected_grade = 14
    respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            text=data,
            status_code=200,
        ),
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        consume=ConsumerType.XML,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == "Alice"
    assert user.grade == expected_grade
    assert user.city == "New York"
    assert user.birthday == datetime.date.fromisoformat("2000-01-01")


@respx.mock
def test_sync_client_path_parameter_without_type():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter):
        pass

    user = get_user("1")

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])


@respx.mock
def test_sync_client_path_parameter_type_not_match():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    respx.get(
        "https://api.example.com/users/1",
    ).mock(
        return_value=Response(
            json=data,
            status_code=200,
        ),
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(InvalidParameterValueError) as e:
        get_user("elphant")

    assert "Invalid value for user_id: Expected <class 'int'>, got <class 'str'>" in str(e)


@respx.mock
def test_sync_client_post_method_with_param_type_and_mapped_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }
    route = respx.post("https://api.example.com/users").mock(
        return_value=Response(
            status_code=200,
            json={
                "name": data["name"],
                "grade": data["grade"],
                "city": data["city"],
                "birthday": data["birthday"],
            },
        ),
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(
        full_name: FormParameter[str, "name"],  # noqa: F821
        grade: FormParameter[int],
        city: FormParameter[str],
        birthday: FormParameter[str],
    ):
        pass

    save_user(full_name="Alice", grade=14, city="New York", birthday="2000-01-01")
    request = route.calls[0].request
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    parsed_body = urllib.parse.parse_qs(request.content.decode())

    assert parsed_body == {
        "name": ["Alice"],
        "grade": ["14"],
        "city": ["New York"],
        "birthday": ["2000-01-01"],
    }
    assert request.content.decode() == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"


@respx.mock
def test_sync_client_post_method_with_only_mapped_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }
    route = respx.post("https://api.example.com/users").mock(
        return_value=Response(
            status_code=200,
            json={
                "name": data["name"],
                "grade": data["grade"],
                "city": data["city"],
                "birthday": data["birthday"],
            },
        ),
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(
        full_name: FormParameter[{"alias": "name"}],  # noqa: F821
        grade: FormParameter[int, "grade"],  # noqa: F821
        city_name: FormParameter["city"],  # noqa: F821
        birthday: FormParameter[str],
    ):
        pass

    save_user(full_name="Alice", grade=14, city_name="New York", birthday="2000-01-01")
    request = route.calls[0].request
    parsed_body = urllib.parse.parse_qs(request.content.decode())

    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert parsed_body == {
        "name": ["Alice"],
        "grade": ["14"],
        "city": ["New York"],
        "birthday": ["2000-01-01"],
    }
    assert request.content.decode() == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"
