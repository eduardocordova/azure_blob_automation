#!/usr/bin/env python3
"""
upload_assets.py - Upload files to Azure Blob Storage

This script recursively traverses a client folder and uploads each file to Azure Blob Storage,
preserving the folder structure. It compares local and remote file hashes (SHA-256) and only
replaces the blob if the content has changed.
"""

import os
import sys
import json
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings
from rich.console import Console
from rich.progress import Progress, TaskID

# Initialize rich console for better output
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("upload_assets")


def load_env_vars() -> Dict[str, str]:
    """Load environment variables from .env file."""
    dotenv.load_dotenv()

    required_vars = [
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME"
    ]

    env_vars = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        env_vars[var] = value

    if missing_vars:
        console.print(f"[bold red]Error: Missing required environment variables: {', '.join(missing_vars)}[/bold red]")
        console.print("[yellow]Please create a .env file with the required variables (see .env.example)[/yellow]")
        sys.exit(1)

    # Set log level from environment or use default
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level))

    return env_vars


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def get_content_type(file_path: Path) -> str:
    """Determine content type based on file extension."""
    extension = file_path.suffix.lower()
    content_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.xml': 'application/xml',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.zip': 'application/zip',
        '.csv': 'text/csv',
    }

    return content_types.get(extension, 'application/octet-stream')


def get_blob_hash(blob_client) -> Optional[str]:
    """Get the SHA-256 hash of a blob from its metadata."""
    try:
        properties = blob_client.get_blob_properties()
        return properties.metadata.get('sha256hash')
    except Exception as e:
        logger.debug(f"Error getting blob hash: {e}")
        return None


def upload_file(
    blob_service_client: BlobServiceClient,
    container_name: str,
    local_file_path: Path,
    blob_path: str,
    progress: Progress,
    task_id: TaskID
) -> Dict[str, Any]:
    """
    Upload a file to Azure Blob Storage if it doesn't exist or has changed.

    Returns a dictionary with upload status information.
    """
    result = {
        "local_path": str(local_file_path),
        "blob_path": blob_path,
        "size_bytes": local_file_path.stat().st_size,
        "content_type": get_content_type(local_file_path),
        "timestamp": datetime.now().isoformat(),
        "status": "skipped",  # Default status
        "message": ""
    }

    # Calculate file hash
    file_hash = calculate_file_hash(local_file_path)
    result["hash"] = file_hash

    # Get blob client
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_path
    )

    # Check if blob exists and compare hashes
    blob_exists = False
    blob_hash = None

    try:
        blob_exists = blob_client.exists()
        if blob_exists:
            blob_hash = get_blob_hash(blob_client)
    except Exception as e:
        logger.error(f"Error checking blob existence: {e}")
        result["status"] = "error"
        result["message"] = str(e)
        return result

    # Skip upload if blob exists and hashes match
    if blob_exists and blob_hash == file_hash:
        progress.update(task_id, advance=1)
        result["status"] = "skipped"
        result["message"] = "File already exists with same hash"
        return result

    # Upload the file
    try:
        content_settings = ContentSettings(content_type=result["content_type"])

        with open(local_file_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=content_settings,
                metadata={"sha256hash": file_hash}
            )

        status = "updated" if blob_exists else "uploaded"
        result["status"] = status
        result["message"] = f"File {status} successfully"
        progress.update(task_id, advance=1)

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        result["status"] = "error"
        result["message"] = str(e)

    return result


def process_directory(
    client_folder: Path,
    env_vars: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Process a client directory and upload all files to Azure Blob Storage.

    Returns a list of dictionaries with upload status information.
    """
    if not client_folder.exists() or not client_folder.is_dir():
        console.print(f"[bold red]Error: Directory not found: {client_folder}[/bold red]")
        sys.exit(1)

    # Connect to Azure Blob Storage
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            env_vars["AZURE_STORAGE_CONNECTION_STRING"]
        )
        container_name = env_vars["AZURE_STORAGE_CONTAINER_NAME"]

        # Check if container exists, create if not
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            console.print(f"[yellow]Container '{container_name}' does not exist. Creating...[/yellow]")
            container_client.create_container()
            console.print(f"[green]Container '{container_name}' created successfully.[/green]")

    except Exception as e:
        console.print(f"[bold red]Error connecting to Azure Blob Storage: {e}[/bold red]")
        sys.exit(1)

    # Get all files in the directory recursively
    all_files = []
    for root, _, files in os.walk(client_folder):
        for file in files:
            file_path = Path(root) / file
            all_files.append(file_path)

    if not all_files:
        console.print(f"[yellow]No files found in {client_folder}[/yellow]")
        return []

    console.print(f"[green]Found {len(all_files)} files to process[/green]")

    # Process files with progress bar
    results = []

    with Progress() as progress:
        task_id = progress.add_task("[cyan]Uploading files...", total=len(all_files))

        for file_path in all_files:
            # Determine blob path (preserve folder structure)
            relative_path = file_path.relative_to(client_folder.parent)
            blob_path = str(relative_path).replace("\\", "/")

            # Upload file
            result = upload_file(
                blob_service_client,
                container_name,
                file_path,
                blob_path,
                progress,
                task_id
            )

            results.append(result)

    return results


def main():
    """Main function to parse arguments and process the client folder."""
    parser = argparse.ArgumentParser(
        description="Upload files from a client folder to Azure Blob Storage."
    )
    parser.add_argument(
        "client_folder",
        help="Name of the client folder to process (e.g., 'acme_co')"
    )
    parser.add_argument(
        "--output",
        help="Path to save the JSON summary (default: stdout)",
        default=None
    )

    args = parser.parse_args()

    # Load environment variables
    env_vars = load_env_vars()

    # Determine client folder path
    # Strip trailing slash if present
    client_folder_name = args.client_folder.rstrip('/')

    # Check if we're already in the data-upload directory
    current_dir = Path.cwd()
    if current_dir.name == "data-upload":
        # We're already in the data-upload directory, so use the client folder directly
        client_folder = Path(client_folder_name)
    else:
        # We're in a parent directory, so prepend data-upload
        base_dir = Path("data-upload")
        client_folder = base_dir / client_folder_name

    console.print(f"[bold]Processing client folder: {client_folder}[/bold]")

    # Process directory and get results
    results = process_directory(client_folder, env_vars)

    # Generate summary
    summary = {
        "client": args.client_folder,
        "timestamp": datetime.now().isoformat(),
        "total_files": len(results),
        "uploaded": sum(1 for r in results if r["status"] == "uploaded"),
        "updated": sum(1 for r in results if r["status"] == "updated"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "files": results
    }

    # Output summary
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        console.print(f"[green]Summary saved to {output_path}[/green]")
    else:
        console.print("[bold]Upload Summary:[/bold]")
        console.print(f"Client: {summary['client']}")
        console.print(f"Total files: {summary['total_files']}")
        console.print(f"Uploaded: {summary['uploaded']}")
        console.print(f"Updated: {summary['updated']}")
        console.print(f"Skipped: {summary['skipped']}")
        console.print(f"Errors: {summary['errors']}")

        if summary['errors'] > 0:
            console.print("[bold red]Errors occurred during upload:[/bold red]")
            for file in summary['files']:
                if file['status'] == 'error':
                    console.print(f"  [red]{file['local_path']}: {file['message']}[/red]")

    return summary


if __name__ == "__main__":
    main()
