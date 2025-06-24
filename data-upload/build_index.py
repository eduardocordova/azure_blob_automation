#!/usr/bin/env python3
"""
build_index.py - Generate an index file for Azure Blob Storage

This script lists all blobs under a client prefix and generates an index.html file
with links to all files. The index file is then uploaded to the same container.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

import dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings
from rich.console import Console

# Initialize rich console for better output
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("build_index")


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
    
    # Get optional variables
    env_vars["INDEX_TITLE"] = os.getenv("INDEX_TITLE", "File Repository")
    
    return env_vars


def list_blobs(
    blob_service_client: BlobServiceClient,
    container_name: str,
    client_prefix: str
) -> List[Dict[str, Any]]:
    """
    List all blobs under a client prefix.
    
    Returns a list of dictionaries with blob information.
    """
    container_client = blob_service_client.get_container_client(container_name)
    
    # Ensure client_prefix ends with a slash if not empty
    if client_prefix and not client_prefix.endswith('/'):
        client_prefix = f"{client_prefix}/"
    
    # List blobs with the specified prefix
    blobs = []
    
    try:
        blob_list = container_client.list_blobs(name_starts_with=client_prefix)
        
        for blob in blob_list:
            # Skip the index file itself
            if blob.name.endswith('/index.html') or blob.name.endswith('/index.md'):
                continue
                
            # Get blob URL
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob.name
            )
            
            # Add blob information to the list
            blobs.append({
                "name": blob.name,
                "display_name": os.path.basename(blob.name),
                "url": blob_client.url,
                "size_bytes": blob.size,
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None
            })
    
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        console.print(f"[bold red]Error listing blobs: {e}[/bold red]")
        sys.exit(1)
    
    return blobs


def generate_html_index(
    blobs: List[Dict[str, Any]],
    client_name: str,
    title: str
) -> str:
    """Generate an HTML index file with links to all blobs."""
    # Group blobs by directory
    blob_groups = {}
    
    for blob in blobs:
        # Get the relative path from the client prefix
        path_parts = blob["name"].split('/')
        
        # Skip the client name part
        if path_parts[0] == client_name:
            path_parts = path_parts[1:]
        
        # Determine the directory path
        if len(path_parts) > 1:
            directory = '/'.join(path_parts[:-1])
        else:
            directory = ""
        
        if directory not in blob_groups:
            blob_groups[directory] = []
        
        blob_groups[directory].append(blob)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {client_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #3498db;
            margin-top: 20px;
        }}
        ul {{
            list-style-type: none;
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        a {{
            color: #2980b9;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .file-size {{
            color: #7f8c8d;
            font-size: 0.8em;
            margin-left: 10px;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 0.8em;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>{title} - {client_name}</h1>
"""

    # Add file listings by directory
    for directory, directory_blobs in sorted(blob_groups.items()):
        if directory:
            html += f"    <h2>{directory}/</h2>\n"
        else:
            html += f"    <h2>Root Directory</h2>\n"
        
        html += "    <ul>\n"
        
        for blob in sorted(directory_blobs, key=lambda x: x["display_name"]):
            file_size = format_file_size(blob["size_bytes"])
            html += f'        <li><a href="{blob["url"]}" target="_blank">{blob["display_name"]}</a>'
            html += f'<span class="file-size">({file_size})</span></li>\n'
        
        html += "    </ul>\n"
    
    # Add timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html += f'    <div class="timestamp">Generated on {current_time}</div>\n'
    
    html += """</body>
</html>
"""
    
    return html


def generate_markdown_index(
    blobs: List[Dict[str, Any]],
    client_name: str,
    title: str
) -> str:
    """Generate a Markdown index file with links to all blobs."""
    # Group blobs by directory
    blob_groups = {}
    
    for blob in blobs:
        # Get the relative path from the client prefix
        path_parts = blob["name"].split('/')
        
        # Skip the client name part
        if path_parts[0] == client_name:
            path_parts = path_parts[1:]
        
        # Determine the directory path
        if len(path_parts) > 1:
            directory = '/'.join(path_parts[:-1])
        else:
            directory = ""
        
        if directory not in blob_groups:
            blob_groups[directory] = []
        
        blob_groups[directory].append(blob)
    
    # Generate Markdown
    md = f"# {title} - {client_name}\n\n"
    
    # Add file listings by directory
    for directory, directory_blobs in sorted(blob_groups.items()):
        if directory:
            md += f"## {directory}/\n\n"
        else:
            md += "## Root Directory\n\n"
        
        for blob in sorted(directory_blobs, key=lambda x: x["display_name"]):
            file_size = format_file_size(blob["size_bytes"])
            md += f"- [{blob['display_name']}]({blob['url']}) ({file_size})\n"
        
        md += "\n"
    
    # Add timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md += f"*Generated on {current_time}*\n"
    
    return md


def format_file_size(size_bytes: int) -> str:
    """Format file size in a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def upload_index(
    blob_service_client: BlobServiceClient,
    container_name: str,
    client_name: str,
    content: str,
    is_markdown: bool = False
) -> str:
    """
    Upload the index file to Azure Blob Storage.
    
    Returns the URL of the uploaded index file.
    """
    # Determine the index file name
    file_extension = "md" if is_markdown else "html"
    content_type = "text/markdown" if is_markdown else "text/html"
    index_blob_name = f"{client_name}/index.{file_extension}"
    
    # Get blob client
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=index_blob_name
    )
    
    # Upload the index file
    try:
        content_settings = ContentSettings(content_type=content_type)
        
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=content_settings
        )
        
        console.print(f"[green]Index file uploaded successfully: {index_blob_name}[/green]")
        
        return blob_client.url
    
    except Exception as e:
        logger.error(f"Error uploading index file: {e}")
        console.print(f"[bold red]Error uploading index file: {e}[/bold red]")
        sys.exit(1)


def main():
    """Main function to parse arguments and generate the index file."""
    parser = argparse.ArgumentParser(
        description="Generate an index file for files in Azure Blob Storage."
    )
    parser.add_argument(
        "client_name",
        help="Name of the client folder to process (e.g., 'acme_co')"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generate a Markdown index file instead of HTML"
    )
    parser.add_argument(
        "--title",
        help="Custom title for the index page (overrides INDEX_TITLE from .env)"
    )
    parser.add_argument(
        "--output",
        help="Path to save a local copy of the index file",
        default=None
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    env_vars = load_env_vars()
    
    # Get title from arguments or environment
    title = args.title or env_vars["INDEX_TITLE"]
    
    # Connect to Azure Blob Storage
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            env_vars["AZURE_STORAGE_CONNECTION_STRING"]
        )
        container_name = env_vars["AZURE_STORAGE_CONTAINER_NAME"]
        
        # Check if container exists
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            console.print(f"[bold red]Error: Container '{container_name}' does not exist.[/bold red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Error connecting to Azure Blob Storage: {e}[/bold red]")
        sys.exit(1)
    
    # List blobs
    console.print(f"[bold]Listing blobs for client: {args.client_name}[/bold]")
    blobs = list_blobs(blob_service_client, container_name, args.client_name)
    
    if not blobs:
        console.print(f"[yellow]No blobs found for client: {args.client_name}[/yellow]")
        sys.exit(0)
    
    console.print(f"[green]Found {len(blobs)} blobs[/green]")
    
    # Generate index content
    if args.markdown:
        index_content = generate_markdown_index(blobs, args.client_name, title)
    else:
        index_content = generate_html_index(blobs, args.client_name, title)
    
    # Save local copy if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        console.print(f"[green]Index file saved locally to: {output_path}[/green]")
    
    # Upload index file
    index_url = upload_index(
        blob_service_client,
        container_name,
        args.client_name,
        index_content,
        args.markdown
    )
    
    console.print(f"[bold green]Index file available at: {index_url}[/bold green]")
    
    return index_url


if __name__ == "__main__":
    main()