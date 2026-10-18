import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage import db as storage_db  # noqa: E402


class TempDbMixin:
    """Point the SQLite store at a throwaway directory for each test."""

    def setUp(self):
        super().setUp()
        self._original_db_path = storage_db.DB_PATH
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="triage_test_"))
        storage_db.DB_PATH = self._tmp_dir / "triage_sessions.db"
        storage_db.init_db()

    def tearDown(self):
        storage_db.DB_PATH = self._original_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        super().tearDown()
