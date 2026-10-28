import os, sqlite3, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("READER_DB", os.path.join(ROOT, "build", "reader.db"))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "reader"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

needs_db = pytest.mark.skipif(not os.path.exists(DB), reason="build/reader.db not built")

@pytest.fixture(scope="session")
def client():
    os.environ["READER_DB"] = DB
    import app as reader_app
    return reader_app.app.test_client()

@pytest.fixture(scope="session")
def con():
    c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
    c.row_factory = sqlite3.Row
    yield c
    c.close()
