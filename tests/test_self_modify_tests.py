from unittest.mock import AsyncMock, patch

import pytest

from jarvis.paths import venv_python
from jarvis.services import self_modify


def test_venv_python_exists():
    assert venv_python().is_file()


@pytest.mark.asyncio
async def test_run_tests_reports_pytest_summary():
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"71 passed in 0.5s\n", b""))
    mock_proc.returncode = 0

    with patch("jarvis.services.self_modify.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await self_modify.run_tests()

    assert result["ok"] is True
    assert "passed" in result["summary"]
