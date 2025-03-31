import datetime
import time

import pytest
import responses
from responses.matchers import json_params_matcher, urlencoded_params_matcher

from dequest.circuit_breaker import CircuitBreaker, CircuitBreakerState
from dequest.clients import sync_client
from dequest.enums import ConsumerType
from dequest.exceptions import DequestError, InvalidParameterValueError
from dequest.parameter_types import FormParameter, JsonBody, PathParameter


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


@responses.activate
def test_sync_client():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])


@responses.activate
def test_sync_client_with_headers():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO, headers={"X-Test-Header": "test"})
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])
    assert api.calls[0].request.headers["X-Test-Header"] == "test"


@responses.activate
def test_sync_client_retry():
    expected_number_of_calls = 3
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json={"message": "Internal Server Error"},
        status=500,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO, retries=3)
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(DequestError):
        get_user(1)

    assert api.call_count == expected_number_of_calls


@responses.activate
def test_sync_client_with_cache():
    expected_number_of_calls = 1
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/4",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO, enable_cache=True)
    def get_user(user_id: PathParameter[int]):
        pass

    for _ in range(4):
        user = get_user(4)

        assert user.name == data["name"]
        assert user.grade == data["grade"]
        assert user.city == data["city"]  # Perform type conversion if base_type is provided (and not Any)

        assert user.birthday == datetime.date.fromisoformat(data["birthday"])

    assert api.call_count == expected_number_of_calls


@responses.activate
def test_sync_client_no_dto_class():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    responses.add(
        responses.GET,
        "https://api.example.com/users/6",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}")
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(user_id=6)

    assert user["name"] == data["name"]
    assert user["grade"] == data["grade"]
    assert user["city"] == data["city"]
    assert user["birthday"] == data["birthday"]


@responses.activate
def test_sync_client_with_headers_and_auth():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json=data,
        status=200,
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
    assert api.calls[0].request.headers["X-Test-Header"] == "test"
    assert api.calls[0].request.headers["Authorization"] == "Bearer my_auth_token"


@responses.activate
def test_sync_client_post_method_with_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.post(
        "https://api.example.com/users",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[urlencoded_params_matcher(data)],
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

    assert api.calls[0].request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert api.calls[0].request.body == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"


@responses.activate
def test_sync_client_post_method_with_json_payload():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }

    api = responses.post(
        "https://api.example.com/users",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[json_params_matcher(data)],
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(name: JsonBody, grade: JsonBody, city_name: JsonBody["city"], birthday: JsonBody):  # noqa: F821
        pass

    save_user(name="Alice", grade=14, city_name="New York", birthday="2000-01-01")

    assert api.calls[0].request.headers["Content-Type"] == "application/json"
    assert api.calls[0].request.body == b'{"name": "Alice", "grade": 14, "city": "New York", "birthday": "2000-01-01"}'


@responses.activate
@pytest.mark.parametrize(
    ("client_calls", "cb_is_open"),
    [
        (1, CircuitBreakerState.CLOSED),
        (2, CircuitBreakerState.CLOSED),
        (3, CircuitBreakerState.OPEN),
    ],
)
def test_sync_client_circute_breaker(client_calls, cb_is_open):
    circut_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    client_retries = 2
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json={"message": "Internal Server Error"},
        status=500,
    )

    @sync_client(
        url="https://api.example.com/users/{user_id}",
        dto_class=UserDTO,
        retries=client_retries,
        circuit_breaker=circut_breaker,
    )
    def get_user(user_id: PathParameter[int]):
        pass

    for _ in range(client_calls):
        with pytest.raises(DequestError):
            get_user(user_id=1)

    assert circut_breaker.get_state() == cb_is_open
    assert api.call_count == client_calls * client_retries


@responses.activate
def test_sync_client_circute_breaker__recovery():
    circut_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
    expected_number_of_calls = 1
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json={"message": "OK"},
        status=200,
    )
    circut_breaker.state = CircuitBreakerState.OPEN
    circut_breaker.last_failure_time = time.time()

    @sync_client(url="https://api.example.com/users/{user_id}", circuit_breaker=circut_breaker)
    def get_user(user_id: PathParameter[int]):
        pass

    result = get_user(user_id=1)

    assert circut_breaker.get_state() == CircuitBreakerState.CLOSED
    assert api.call_count == expected_number_of_calls
    assert result == {"message": "OK"}


@responses.activate
def test_sync_client_circute_breaker__fallback():
    def fallback_response(user_id):
        return {"message": "Service temporarily unavailable, please try later."}

    circut_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30, fallback_function=fallback_response)
    expected_number_of_calls = 0
    api = responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json={"message": "Internal Server Error"},
        status=500,
    )
    circut_breaker.state = CircuitBreakerState.OPEN
    circut_breaker.last_failure_time = time.time()

    @sync_client(url="https://api.example.com/users/{user_id}", circuit_breaker=circut_breaker)
    def get_user(user_id: PathParameter[int]):
        pass

    result = get_user(user_id=1)

    assert circut_breaker.get_state() == CircuitBreakerState.OPEN
    assert api.call_count == expected_number_of_calls
    assert result == {"message": "Service temporarily unavailable, please try later."}


@responses.activate
def test_sync_client_xml_response():
    data = "<student><name>Alice</name><grade>14</grade><city>New York</city><birthday>2000-01-01</birthday></student>"
    expected_grade = 14
    responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        body=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO, consume=ConsumerType.XML)
    def get_user(user_id: PathParameter[int]):
        pass

    user = get_user(1)

    assert user.name == "Alice"
    assert user.grade == expected_grade
    assert user.city == "New York"
    assert user.birthday == datetime.date.fromisoformat("2000-01-01")


@responses.activate
def test_sync_client_path_parameter_without_type():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter):
        pass

    user = get_user("1")

    assert user.name == data["name"]
    assert user.grade == data["grade"]
    assert user.city == data["city"]
    assert user.birthday == datetime.date.fromisoformat(data["birthday"])


@responses.activate
def test_sync_client_path_parameter_type_not_match():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json=data,
        status=200,
    )

    @sync_client(url="https://api.example.com/users/{user_id}", dto_class=UserDTO)
    def get_user(user_id: PathParameter[int]):
        pass

    with pytest.raises(InvalidParameterValueError) as e:
        get_user("elphant")

    assert "Invalid value for user_id: Expected <class 'int'>, got <class 'str'>" in str(e)


@responses.activate
def test_sync_client_post_method_with_param_type_and_mapped_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.post(
        "https://api.example.com/users",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[urlencoded_params_matcher(data)],
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

    assert api.calls[0].request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert api.calls[0].request.body == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"


@responses.activate
def test_sync_client_post_method_with_only_mapped_form_data():
    data = {
        "name": "Alice",
        "grade": "14",
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.post(
        "https://api.example.com/users",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[urlencoded_params_matcher(data)],
    )

    @sync_client(url="https://api.example.com/users", dto_class=UserDTO, method="POST")
    def save_user(
        full_name: FormParameter[{"alias": "name"}],  # noqa: F821
        grade: FormParameter[int, "grade"],  # noqa: F821
        city_name: FormParameter["city"],  # noqa: F821
        birthday: FormParameter[str,],
    ):
        pass

    save_user(full_name="Alice", grade=14, city_name="New York", birthday="2000-01-01")

    assert api.calls[0].request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert api.calls[0].request.body == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"
