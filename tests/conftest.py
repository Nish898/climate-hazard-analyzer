import os

# Must be set before `app` is imported: tests should not write log files or inherit a developer's .env.
os.environ["LOG_TO_FILE"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.main import limiter

    limiter.reset()
    yield
