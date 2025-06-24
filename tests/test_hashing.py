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
from upload_assets import sha256_of_file


def test_sha256_of_file(tmp_path: Path) -> None:
    file = tmp_path / "sample.txt"
    file.write_text("hello")
    assert sha256_of_file(file) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
