from dequest.utils import map_json_to_dto


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
