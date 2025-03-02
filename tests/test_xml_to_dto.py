import pytest

from dequest.utils import map_xml_to_dto


class SimpleDTO:
    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = int(age) if age is not None else None


class NestedDTO:
    title: str
    details: SimpleDTO

    def __init__(self, title: str, details: SimpleDTO):
        self.title = title
        self.details = details


def test_mapping_attributes():
    xml_data = '<Person name="John" age="30" />'
    expected_age = 30

    dto = map_xml_to_dto(SimpleDTO, xml_data)

    assert dto.name == "John"
    assert dto.age == expected_age


def test_mapping_children():
    xml_data = "<Person><name>John</name><age>30</age></Person>"
    expected_age = 30

    dto = map_xml_to_dto(SimpleDTO, xml_data)

    assert dto.name == "John"
    assert dto.age == expected_age


def test_nested_dto_children():
    xml_data = "<Book><title>Python Guide</title><details><name>Alice</name><age>25</age></details></Book>"
    expected_age = 25

    dto = map_xml_to_dto(NestedDTO, xml_data)

    assert dto.title == "Python Guide"
    assert dto.details.name == "Alice"
    assert dto.details.age == expected_age


def test_missing_fields():
    xml_data = '<Person name="John" />'  # Missing age

    with pytest.raises(TypeError) as e:
        map_xml_to_dto(SimpleDTO, xml_data)

    assert "missing 1 required positional argument" in str(e)


def test_empty_xml():
    xml_data = "<Person ><name></name><age></age></Person>"

    dto = map_xml_to_dto(SimpleDTO, xml_data)

    assert dto.name is None
    assert dto.age is None


def test_multiple_records():
    xml_data = '<People><Person name="Alice" age="25" /><Person name="Bob" age="30" /></People>'
    expected_first_record_age = 25
    expected_second_record_age = 30
    expected_records_count = 2

    dtos = map_xml_to_dto(SimpleDTO, xml_data)

    assert isinstance(dtos, list)
    assert len(dtos) == expected_records_count
    assert dtos[0].name == "Alice"
    assert dtos[0].age == expected_first_record_age
    assert dtos[1].name == "Bob"
    assert dtos[1].age == expected_second_record_age


def test_nested_dto_attributes_and_children():
    xml_data = '<Book title="Python Guide"><details name="Alice" age="25" /></Book>'
    expected_age = 25

    dto = map_xml_to_dto(NestedDTO, xml_data)

    assert dto.title == "Python Guide"
    assert dto.details.name == "Alice"
    assert dto.details.age == expected_age
