import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
def ensure_main_event_loop():
    """Keep a compatibility loop available for legacy sync tests."""
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    yield
