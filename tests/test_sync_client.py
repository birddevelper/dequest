import datetime

import pytest
import responses
from responses.matchers import json_params_matcher, urlencoded_params_matcher

from dequest.clients.sync_client import sync_client
from dequest.exceptions import DequestError


class UserDTO:
    name: str
    grade: int
    city: str
    birthday: datetime.date

    def __init__(self, name, grade, city, birthday):
        self.name = name
        self.grade = grade
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
        "https://api.example.com/students/1",
        json=data,
        status=200,
    )

    @sync_client(UserDTO)
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

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
        "https://api.example.com/students/1",
        json=data,
        status=200,
    )

    @sync_client(UserDTO, headers={"X-Test-Header": "test"})
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

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
        "https://api.example.com/students/1",
        json={"message": "Internal Server Error"},
        status=500,
    )

    @sync_client(UserDTO, retries=3)
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

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
        "https://api.example.com/students/4",
        json=data,
        status=200,
    )

    @sync_client(UserDTO, enable_cache=True)
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

    for _ in range(4):
        user = get_user(4)

        assert user.name == data["name"]
        assert user.grade == data["grade"]
        assert user.city == data["city"]
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
        "https://api.example.com/students/6",
        json=data,
        status=200,
    )

    @sync_client()
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

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
        "https://api.example.com/students/1",
        json=data,
        status=200,
    )

    @sync_client(UserDTO, headers={"X-Test-Header": "test"}, auth_token="my_auth_token")  # noqa: S106
    def get_user(user_id):
        return {
            "url": f"https://api.example.com/students/{user_id}",
        }

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
        "https://api.example.com/students",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[urlencoded_params_matcher(data)],
    )

    @sync_client(UserDTO, method="POST")
    def save_user(name, grade, city, birthday):
        return {
            "url": "https://api.example.com/students",
            "data": {"name": name, "grade": grade, "city": city, "birthday": birthday},
        }

    save_user(name="Alice", grade=14, city="New York", birthday="2000-01-01")

    assert (
        api.calls[0].request.headers["Content-Type"]
        == "application/x-www-form-urlencoded"
    )
    assert (
        api.calls[0].request.body
        == "name=Alice&grade=14&city=New+York&birthday=2000-01-01"
    )


@responses.activate
def test_sync_client_post_method_with_json_payload():
    data = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.post(
        "https://api.example.com/students",
        json={
            "name": data["name"],
            "grade": data["grade"],
            "city": data["city"],
            "birthday": data["birthday"],
        },
        status=200,
        match=[json_params_matcher(data)],
    )

    @sync_client(UserDTO, method="POST")
    def save_user(name, grade, city, birthday):
        return {
            "url": "https://api.example.com/students",
            "json_body": {
                "name": name,
                "grade": grade,
                "city": city,
                "birthday": birthday,
            },
        }

    save_user(name="Alice", grade=14, city="New York", birthday="2000-01-01")

    assert api.calls[0].request.headers["Content-Type"] == "application/json"
    assert (
        api.calls[0].request.body
        == b'{"name": "Alice", "grade": 14, "city": "New York", "birthday": "2000-01-01"}'
    )
