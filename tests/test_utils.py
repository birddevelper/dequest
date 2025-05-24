from collections.abc import Iterator

import pytest

from dequest.utils import get_next_delay, map_json_to_dto


class AddressDTO:
    street: str
    city: str

    def __init__(self, street, city):
        self.street = street
        self.city = city


class OrdertDTO:
    name: str
    count: int
    fee: float
    total_price: float

    def __init__(self, name, count, fee):
        self.name = name
        self.count = count
        self.fee = fee
        self.total_price = count * fee


class UserDTO:
    name: str
    address: AddressDTO
    friends: list[str]

    def __init__(self, name, address, friends):
        self.name = name
        self.address = address
        self.friends = friends


def test_mapping_nested_dto():
    data = {
        "name": "John",
        "address": {"street": "123 Main St", "city": "Hometown"},
        "friends": ["Alice", "Bob"],
    }

    user = map_json_to_dto(UserDTO, data)

    assert user.name == data["name"]
    assert isinstance(user.address, AddressDTO)
    assert user.address.street == data["address"]["street"]
    assert user.address.city == data["address"]["city"]
    assert user.friends == data["friends"]


def test_mapping_non_nested_dto():
    data = {"street": "123 Main St", "city": "Hometown"}

    address = map_json_to_dto(AddressDTO, data)

    assert address.street == data["street"]
    assert address.city == data["city"]


def test_mapping_partial_dto_attributes_in_constructor():
    data = {"name": "PopCorn", "count": 2, "fee": 10.0}

    order = map_json_to_dto(OrdertDTO, data)

    assert order.name == data["name"]
    assert order.count == data["count"]
    assert order.fee == data["fee"]
    assert order.total_price == data["count"] * data["fee"]


def delay_gen() -> Iterator[float]:
    yield 1.5
    yield 2.5


def test_get_next_delay_with_float():
    expected_delay = 2.0

    assert get_next_delay(expected_delay) == expected_delay


def test_get_next_delay_with_generator():
    expected_first_delay = 1.5
    expected_second_delay = 2.5
    gen = delay_gen()

    assert get_next_delay(gen) == expected_first_delay
    assert get_next_delay(gen) == expected_second_delay


def test_get_next_delay_with_none():
    assert get_next_delay(None) is None


def test_get_next_delay_generator_exhausted():
    gen = iter([])

    with pytest.raises(StopIteration):
        get_next_delay(gen)
