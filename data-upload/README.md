# Azure Blob Storage Asset Manager

This project provides tools for uploading files to Azure Blob Storage and generating an index file with links to all uploaded files.

## Features

- Upload files to Azure Blob Storage preserving folder structure
- Compare file hashes to avoid redundant uploads
- Generate HTML or Markdown index files with direct download links
- Support for various file types with proper content types
- Clean CLI interface with progress tracking

## Prerequisites

- Python 3.10 or higher
- Azure Storage Account with a container
- Proper permissions to upload and list blobs

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd data-upload
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Azure Storage credentials:
   ```bash
   cp .env.example .env
   ```
   
   Then edit the `.env` file and add your Azure Storage credentials:
   ```
   AZURE_STORAGE_CONNECTION_STRING=your_connection_string
   AZURE_STORAGE_CONTAINER_NAME=your_container_name
   ```

## Usage

### Uploading Files

To upload files from a client folder to Azure Blob Storage:

```bash
python upload_assets.py <client_folder>
```

Example:
```bash
python upload_assets.py mibor
```

This will upload all files from the `data-upload/mibor` directory to Azure Blob Storage, preserving the folder structure.

Options:
- `--output <file>`: Save the JSON summary to a file instead of printing to stdout

### Generating Index

To generate an index file with links to all uploaded files:

```bash
python build_index.py <client_folder>
```

Example:
```bash
python build_index.py mibor
```

This will generate an HTML index file with links to all files under the `mibor` prefix in Azure Blob Storage.

Options:
- `--markdown`: Generate a Markdown index file instead of HTML
- `--title "Custom Title"`: Set a custom title for the index page
- `--output <file>`: Save a local copy of the index file

## File Structure

```
data-upload/
├─ .env.example         # Example environment variables
├─ requirements.txt     # Python dependencies
├─ upload_assets.py     # Script for uploading files
├─ build_index.py       # Script for generating index
├─ README.md            # This file
└─ tests/               # Unit tests
    ├─ test_hashing.py
    └─ test_upload_logic.py
```

## How It Works

### upload_assets.py

1. Recursively traverses the client folder
2. Calculates SHA-256 hash for each file
3. Checks if the file already exists in Azure Blob Storage with the same hash
4. Uploads only new or modified files
5. Returns a JSON summary of uploaded, updated, and skipped files

### build_index.py

1. Lists all blobs under the client prefix in Azure Blob Storage
2. Groups files by directory
3. Generates an HTML or Markdown index file with links to all files
4. Uploads the index file to Azure Blob Storage
5. Returns the URL of the index file

## Development

### Running Tests

```bash
pytest
```

## License

[MIT License](LICENSE)