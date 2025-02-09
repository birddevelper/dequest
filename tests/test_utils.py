from dequest.utils import map_to_dto


class AddressDTO:
    street: str
    city: str

    def __init__(self, street, city):
        self.street = street
        self.city = city


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

    user = map_to_dto(UserDTO, data)

    assert user.name == data["name"]
    assert isinstance(user.address, AddressDTO)
    assert user.address.street == data["address"]["street"]
    assert user.address.city == data["address"]["city"]
    assert user.friends == data["friends"]


def test_mapping_non_nested_dto():
    data = {"street": "123 Main St", "city": "Hometown"}

    address = map_to_dto(AddressDTO, data)

    assert address.street == data["street"]
    assert address.city == data["city"]
