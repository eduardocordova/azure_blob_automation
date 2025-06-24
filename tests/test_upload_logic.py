import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import types

if "dotenv" not in sys.modules:
    dotenv_module = types.ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dotenv_module

if "azure.storage.blob" not in sys.modules:
    blob_module = types.ModuleType("azure.storage.blob")
    blob_module.BlobServiceClient = object
    sys.modules["azure.storage.blob"] = blob_module

if "rich.progress" not in sys.modules:
    progress_module = types.ModuleType("rich.progress")
    progress_module.Progress = object
    sys.modules["rich.progress"] = progress_module

from pathlib import Path
from types import SimpleNamespace
from upload_assets import upload_file


class DummyBlobClient:
    def __init__(self, exists: bool, metadata: dict | None = None):
        self._exists = exists
        self.metadata = metadata or {}
        self.uploaded = False

    def get_blob_properties(self):
        if not self._exists:
            raise Exception("not found")
        return SimpleNamespace(metadata=self.metadata)

    def upload_blob(self, data, overwrite: bool, metadata: dict):
        self.uploaded = True
        self.metadata = metadata


class DummyService:
    def __init__(self, blob_client: DummyBlobClient):
        self._blob_client = blob_client

    def get_blob_client(self, container: str, blob_path: str):
        return self._blob_client


def test_upload_skips_when_hash_matches(tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("content")
    sha = "hash"
    blob = DummyBlobClient(True, {"sha256": sha})
    service = DummyService(blob)
    changed = upload_file(service, "cont", "path", file, sha)
    assert not changed
    assert not blob.uploaded


def test_upload_when_different_hash(tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("content")
    sha = "hash"
    blob = DummyBlobClient(True, {"sha256": "old"})
    service = DummyService(blob)
    changed = upload_file(service, "cont", "path", file, sha)
    assert changed
    assert blob.uploaded
    assert blob.metadata["sha256"] == sha
