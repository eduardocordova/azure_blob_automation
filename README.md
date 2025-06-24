# Azure Blob Automation

This project provides simple scripts to upload assets to Azure Blob Storage and build an index file for easy browsing.

## Setup
1. Clone the repository.
2. Create a `.env` file based on `.env.example` with your storage connection string and container name.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Upload assets
```
python upload_assets.py <client_folder>
```
This will upload the folder under `data-upload/<client_folder>` to the configured container, preserving the hierarchy. Only changed files are uploaded.

### Build index
```
python build_index.py <client_folder>
```
Generates an `index.html` listing all blobs under the prefix and uploads it to the container.

## Testing
Run unit tests with:
```bash
pytest
```
