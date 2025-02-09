import pytest
import responses

from dequest.clients.sync_client import perform_request


@responses.activate
def test_perform_request_no_cache():
    expectred_number_of_calls = 4
    api_response = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.GET,
        "https://api.example.com/students/1",
        json=api_response,
        status=200,
    )

    for _ in range(4):
        response = perform_request("https://api.example.com/students/1")

        assert response == api_response

    assert api.call_count == expectred_number_of_calls


@responses.activate
def test_perform_request_cache_enabled():
    expectred_number_of_calls = 1
    api_response = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.GET,
        "https://api.example.com/students/1",
        json=api_response,
        status=200,
    )

    for _ in range(4):
        response = perform_request(
            "https://api.example.com/students/1",
            enable_cache=True,
        )

        assert response == api_response

    assert api.call_count == expectred_number_of_calls


@responses.activate
def test_perform_request_post_method():
    expectred_number_of_calls = 4
    api_response = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.POST,
        "https://api.example.com/students/1",
        json=api_response,
        status=200,
    )

    for _ in range(4):
        response = perform_request("https://api.example.com/students/1", method="POST")

        assert response == api_response

    assert api.call_count == expectred_number_of_calls


@responses.activate
@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_perform_request_not_allowed_methods_with_cache(method):
    expectred_number_of_calls = 0
    api_response = {
        "name": "Alice",
        "grade": 14,
        "city": "New York",
        "birthday": "2000-01-01",
    }
    api = responses.add(
        responses.POST,
        "https://api.example.com/students/1",
        json=api_response,
        status=200,
    )

    with pytest.raises(ValueError):
        perform_request(
            "https://api.example.com/students/1",
            method=method,
            enable_cache=True,
        )

    assert api.call_count == expectred_number_of_calls
