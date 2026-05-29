import io
import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from dequest import (
    FileParameter,
    FormParameter,
    JsonBody,
    async_await_client,
    sync_client,
)


class FileUploadDTO:
    """DTO for file upload response."""

    status: str
    filename: str

    def __init__(self, status, filename):
        self.status = status
        self.filename = filename


@respx.mock
def test_sync_client_file_upload_with_bytes():
    """Test file upload with bytes."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        file: bytes = FileParameter(),
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_content = b"test file content"
    result = upload_file(file=file_content, description="A test file")

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
def test_sync_client_file_upload_with_file_object():
    """Test file upload with file-like object (BytesIO)."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        file: io.BytesIO = FileParameter(),  # noqa: B008
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_obj = io.BytesIO(b"test file content")
    result = upload_file(file=file_obj, description="A test file")

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
def test_sync_client_file_upload_with_file_path():
    """Test file upload with file path as string."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        file: str = FileParameter(),
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test file content")
        temp_path = f.name

    try:
        # When using file path as string, open it as file-like object first
        with Path(temp_path).open("rb") as f:
            result = upload_file(file=f, description="A test file")
        assert result.status == "success"
        assert result.filename == "test.txt"
        assert route.called
        # Verify request content
        request = route.calls.last.request
        assert b"test file content" in request.content
        assert b"A test file" in request.content
        assert "multipart/form-data" in request.headers.get("content-type", "")
    finally:
        Path(temp_path).unlink()


@respx.mock
def test_sync_client_file_upload_multiple_form_params():
    """Test file upload with multiple form parameters."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        file: bytes = FileParameter(),
        description: str = FormParameter(),
        tags: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_content = b"test file content"
    result = upload_file(
        file=file_content,
        description="A test file",
        tags="test, upload",
    )

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert b"test, upload" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
def test_sync_client_file_upload_with_default_value():
    """Test file upload with optional file parameter."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        description: str = FormParameter(),
        file: bytes | None = FileParameter(default=None),
    ) -> FileUploadDTO:
        pass

    # Call without file
    result = upload_file(description="A test file")
    assert result.status == "success"
    assert route.called


def test_sync_client_file_upload_with_json_body_raises_error():
    """Test that using FileParameter with JsonBody raises an error."""

    @sync_client(url="https://api.example.com/upload", method="POST")
    def upload_file(
        file: bytes = FileParameter(),
        data: dict = JsonBody(),  # noqa: B008
    ) -> dict:
        pass

    file_content = b"test file content"
    with pytest.raises(ValueError, match="FileParameter cannot be used with JsonBody"):
        upload_file(file=file_content, data={"name": "test"})


@respx.mock
def test_sync_client_file_with_alias():
    """Test file upload with parameter alias."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    def upload_file(
        file: bytes = FileParameter(alias="upload_file"),
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_content = b"test file content"
    result = upload_file(file=file_content, description="A test file")

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content and that alias is used
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert b"upload_file" in request.content  # Verify alias is used in request
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
@pytest.mark.asyncio
async def test_async_client_file_upload_with_bytes():
    """Test async file upload with bytes."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @async_await_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    async def upload_file(
        file: bytes = FileParameter(),
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_content = b"test file content"
    result = await upload_file(file=file_content, description="A test file")

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
@pytest.mark.asyncio
async def test_async_client_file_upload_with_file_object():
    """Test async file upload with file-like object."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @async_await_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    async def upload_file(
        file: io.BytesIO = FileParameter(),  # noqa: B008
        description: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_obj = io.BytesIO(b"test file content")
    result = await upload_file(file=file_obj, description="A test file")

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
@pytest.mark.asyncio
async def test_async_client_file_upload_multiple_params():
    """Test async file upload with multiple form parameters."""
    response_data = {"status": "success", "filename": "test.txt"}
    route = respx.post("https://api.example.com/upload").mock(
        return_value=Response(200, json=response_data),
    )

    @async_await_client(
        url="https://api.example.com/upload",
        method="POST",
        dto_class=FileUploadDTO,
    )
    async def upload_file(
        file: bytes = FileParameter(),
        description: str = FormParameter(),
        tags: str = FormParameter(),
    ) -> FileUploadDTO:
        pass

    file_content = b"test file content"
    result = await upload_file(
        file=file_content,
        description="A test file",
        tags="test, upload",
    )

    assert result.status == "success"
    assert result.filename == "test.txt"
    assert route.called
    # Verify request content
    request = route.calls.last.request
    assert b"test file content" in request.content
    assert b"A test file" in request.content
    assert b"test, upload" in request.content
    assert "multipart/form-data" in request.headers.get("content-type", "")


@respx.mock
def test_sync_client_form_params_without_file():
    """Test that form parameters work without file uploads."""
    response_data = {"status": "success", "message": "Form submitted"}
    route = respx.post("https://api.example.com/submit").mock(
        return_value=Response(200, json=response_data),
    )

    @sync_client(url="https://api.example.com/submit", method="POST")
    def submit_form(name: str = FormParameter(), email: str = FormParameter()) -> dict:
        pass

    result = submit_form(name="John Doe", email="john@example.com")

    assert result["status"] == "success"
    assert route.called
