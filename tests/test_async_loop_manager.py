import asyncio
import threading
from unittest.mock import patch

import pytest

from dequest.utils import AsyncLoopManager  # Adjust import path as needed


@pytest.mark.asyncio
async def test_get_event_loop_when_running():
    """Test that get_event_loop returns the current running loop when inside an async function."""
    loop = AsyncLoopManager.get_event_loop()
    assert loop == asyncio.get_running_loop(), "Expected get_event_loop to return the running loop"


def test_get_event_loop_creates_new_loop():
    """Test that get_event_loop creates a new event loop when no running loop exists."""

    def run_in_thread(result_holder):
        """Helper function to call get_event_loop from a new thread."""
        result_holder.append(AsyncLoopManager.get_event_loop())

    result_holder = []
    thread = threading.Thread(target=run_in_thread, args=(result_holder,))
    thread.start()
    thread.join()

    assert len(result_holder) == 1, "Expected one event loop to be created"
    assert isinstance(result_holder[0], asyncio.AbstractEventLoop), "Expected an event loop instance"


def test_get_event_loop_handles_runtime_error():
    """Test that get_event_loop correctly handles RuntimeError and creates a background loop."""
    with patch("asyncio.get_running_loop", side_effect=RuntimeError):
        loop = AsyncLoopManager.get_event_loop()
        assert isinstance(loop, asyncio.AbstractEventLoop), "Expected a new background event loop to be created"


def test_get_event_loop_creates_only_one_background_loop():
    """Test that get_event_loop does not create multiple background loops."""
    with patch("asyncio.get_running_loop", side_effect=RuntimeError):
        loop1 = AsyncLoopManager.get_event_loop()
        loop2 = AsyncLoopManager.get_event_loop()

    assert loop1 is loop2, "Expected the same background loop to be returned each time"


def test_get_event_loop_thread_safety():
    """Test that multiple threads calling get_event_loop concurrently do not create multiple loops."""
    results = []
    threads = [threading.Thread(target=lambda: results.append(AsyncLoopManager.get_event_loop())) for _ in range(5)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(results)) == 1, "Expected all threads to get the same event loop instance"
