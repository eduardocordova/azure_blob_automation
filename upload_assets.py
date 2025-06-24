#!/usr/bin/env python3
"""Upload assets from local folder to Azure Blob Storage."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from rich.progress import Progress
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def sha256_of_file(path: Path) -> str:
    hash_sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha.update(chunk)
    return hash_sha.hexdigest()


def load_config() -> Dict[str, str]:
    load_dotenv()
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_CONTAINER_NAME")
    if not conn_str or not container_name:
        raise EnvironmentError("Missing Azure configuration in .env")
    return {"conn_str": conn_str, "container_name": container_name}


def get_blob_service_client(conn_str: str) -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(conn_str)


def upload_file(blob_service: BlobServiceClient, container: str, blob_path: str, file_path: Path, sha256: str) -> bool:
    blob_client = blob_service.get_blob_client(container, blob_path)
    try:
        props = blob_client.get_blob_properties()
        remote_sha = props.metadata.get("sha256") if props.metadata else None
        if remote_sha == sha256:
            logging.info("Skipping %s (no changes)", blob_path)
            return False
    except Exception:
        pass  # blob doesn't exist
    with file_path.open("rb") as data:
        blob_client.upload_blob(
            data,
            overwrite=True,
            metadata={"sha256": sha256},
        )
    logging.info("Uploaded %s", blob_path)
    return True


def traverse_and_upload(client: str) -> List[Dict[str, str]]:
    cfg = load_config()
    service = get_blob_service_client(cfg["conn_str"])
    container = cfg["container_name"]
    local_root = Path("data-upload") / client
    if not local_root.is_dir():
        raise FileNotFoundError(f"Client folder {local_root} not found")

    results = []
    with Progress() as progress:
        task = progress.add_task("Uploading", total=None)
        for path in local_root.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(local_root)
                blob_path = f"{client}/{rel_path.as_posix()}"
                sha = sha256_of_file(path)
                uploaded = upload_file(service, container, blob_path, path, sha)
                if uploaded:
                    results.append({"blob": blob_path, "sha256": sha})
        progress.update(task, completed=1)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload assets to Azure Blob Storage")
    parser.add_argument("client", help="Client folder name under data-upload")
    args = parser.parse_args()
    uploads = traverse_and_upload(args.client)
    print(json.dumps({"uploaded": uploads}, indent=2))


if __name__ == "__main__":
    main()
