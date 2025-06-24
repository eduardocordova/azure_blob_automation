#!/usr/bin/env python3
"""
Tests for upload logic in upload_assets.py
"""

import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import json

# Add parent directory to path to import from upload_assets
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from upload_assets import upload_file, get_content_type, calculate_file_hash


class TestUploadLogic(unittest.TestCase):
    """Test cases for upload logic functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary test file
        self.test_content = b"Test content for upload"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(self.test_content)
            self.temp_path = Path(temp_file.name)
        
        # Calculate file hash
        self.file_hash = calculate_file_hash(self.temp_path)
        
        # Mock objects
        self.mock_blob_service_client = MagicMock()
        self.mock_blob_client = MagicMock()
        self.mock_progress = MagicMock()
        self.mock_task_id = MagicMock()
        
        # Set up the mock blob service client to return our mock blob client
        self.mock_blob_service_client.get_blob_client.return_value = self.mock_blob_client

    def tearDown(self):
        """Clean up after tests."""
        if self.temp_path.exists():
            os.unlink(self.temp_path)

    def test_get_content_type(self):
        """Test content type detection based on file extension."""
        # Test common file types
        self.assertEqual(get_content_type(Path("test.txt")), "text/plain")
        self.assertEqual(get_content_type(Path("test.html")), "text/html")
        self.assertEqual(get_content_type(Path("test.pdf")), "application/pdf")
        self.assertEqual(get_content_type(Path("test.jpg")), "image/jpeg")
        self.assertEqual(get_content_type(Path("test.png")), "image/png")
        self.assertEqual(get_content_type(Path("test.docx")), 
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # Test unknown file type
        self.assertEqual(get_content_type(Path("test.unknown")), "application/octet-stream")

    @patch('upload_assets.get_blob_hash')
    def test_upload_new_file(self, mock_get_blob_hash):
        """Test uploading a new file that doesn't exist in the container."""
        # Set up mocks
        self.mock_blob_client.exists.return_value = False
        mock_get_blob_hash.return_value = None
        
        # Call the function
        result = upload_file(
            self.mock_blob_service_client,
            "test-container",
            self.temp_path,
            "test/path.txt",
            self.mock_progress,
            self.mock_task_id
        )
        
        # Verify the result
        self.assertEqual(result["status"], "uploaded")
        self.assertEqual(result["blob_path"], "test/path.txt")
        self.assertEqual(result["hash"], self.file_hash)
        self.assertEqual(result["content_type"], "text/plain")
        
        # Verify the mock calls
        self.mock_blob_service_client.get_blob_client.assert_called_once_with(
            container="test-container",
            blob="test/path.txt"
        )
        self.mock_blob_client.exists.assert_called_once()
        self.mock_blob_client.upload_blob.assert_called_once()
        self.mock_progress.update.assert_called_once_with(self.mock_task_id, advance=1)

    @patch('upload_assets.get_blob_hash')
    def test_update_existing_file(self, mock_get_blob_hash):
        """Test updating an existing file with different content."""
        # Set up mocks
        self.mock_blob_client.exists.return_value = True
        mock_get_blob_hash.return_value = "different-hash"
        
        # Call the function
        result = upload_file(
            self.mock_blob_service_client,
            "test-container",
            self.temp_path,
            "test/path.txt",
            self.mock_progress,
            self.mock_task_id
        )
        
        # Verify the result
        self.assertEqual(result["status"], "updated")
        
        # Verify the mock calls
        self.mock_blob_client.upload_blob.assert_called_once()
        self.mock_progress.update.assert_called_once_with(self.mock_task_id, advance=1)

    @patch('upload_assets.get_blob_hash')
    def test_skip_identical_file(self, mock_get_blob_hash):
        """Test skipping a file that already exists with the same hash."""
        # Set up mocks
        self.mock_blob_client.exists.return_value = True
        mock_get_blob_hash.return_value = self.file_hash
        
        # Call the function
        result = upload_file(
            self.mock_blob_service_client,
            "test-container",
            self.temp_path,
            "test/path.txt",
            self.mock_progress,
            self.mock_task_id
        )
        
        # Verify the result
        self.assertEqual(result["status"], "skipped")
        
        # Verify the mock calls
        self.mock_blob_client.upload_blob.assert_not_called()
        self.mock_progress.update.assert_called_once_with(self.mock_task_id, advance=1)

    @patch('upload_assets.get_blob_hash')
    def test_upload_error_handling(self, mock_get_blob_hash):
        """Test error handling during upload."""
        # Set up mocks
        self.mock_blob_client.exists.return_value = True
        mock_get_blob_hash.return_value = "different-hash"
        self.mock_blob_client.upload_blob.side_effect = Exception("Test upload error")
        
        # Call the function
        result = upload_file(
            self.mock_blob_service_client,
            "test-container",
            self.temp_path,
            "test/path.txt",
            self.mock_progress,
            self.mock_task_id
        )
        
        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertIn("Test upload error", result["message"])


if __name__ == "__main__":
    unittest.main()