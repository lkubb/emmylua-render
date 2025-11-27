from pathlib import Path

import pytest


@pytest.fixture
def files() -> Path:
    files_dir = Path(__file__).parent / "files"
    return files_dir.resolve()
