#!/usr/bin/env python3
"""Generate an index.html listing all blobs for a client."""
from __future__ import annotations

import argparse
import datetime as dt
import logging
from pathlib import Path
from typing import Dict, List

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang='en'>
<head><meta charset='UTF-8'><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p>Generated on {date}</p>
<ul>
{items}
</ul>
</body>
</html>
"""


def load_config() -> Dict[str, str]:
    load_dotenv()
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_CONTAINER_NAME")
    if not conn_str or not container_name:
        raise EnvironmentError("Missing Azure configuration in .env")
    return {"conn_str": conn_str, "container_name": container_name}


def get_blob_service_client(conn_str: str) -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(conn_str)


def list_blobs(service: BlobServiceClient, container: str, prefix: str) -> List[str]:
    container_client = service.get_container_client(container)
    return [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]


def build_html(blobs: List[str], title: str) -> str:
    items = "\n".join(
        f"<li><a href='{Path(name).name}'>{Path(name).name}</a></li>" for name in blobs
    )
    return HTML_TEMPLATE.format(title=title, date=dt.datetime.utcnow().isoformat(), items=items)


def upload_index(service: BlobServiceClient, container: str, blob_path: str, content: str) -> None:
    blob_client = service.get_blob_client(container, blob_path)
    blob_client.upload_blob(content, overwrite=True, content_type="text/html")
    logging.info("Uploaded index to %s", blob_path)


def generate_and_upload_index(client: str) -> None:
    cfg = load_config()
    service = get_blob_service_client(cfg["conn_str"])
    container = cfg["container_name"]
    prefix = f"{client}/"
    blobs = list_blobs(service, container, prefix)
    html = build_html(blobs, title=f"Index of {client}")
    upload_index(service, container, f"{client}/index.html", html)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build index.html for uploaded blobs")
    parser.add_argument("client", help="Client folder name under data-upload")
    args = parser.parse_args()
    generate_and_upload_index(args.client)


if __name__ == "__main__":
    main()
