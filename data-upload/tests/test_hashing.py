#!/usr/bin/env python3
"""
Tests for file hashing functionality in upload_assets.py
"""

import os
import tempfile
import hashlib
from pathlib import Path
import sys
import unittest

# Add parent directory to path to import from upload_assets
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from upload_assets import calculate_file_hash


class TestHashing(unittest.TestCase):
    """Test cases for file hashing functionality."""

    def test_empty_file_hash(self):
        """Test hash calculation for an empty file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Calculate hash using our function
            file_hash = calculate_file_hash(temp_path)
            
            # Calculate expected hash (SHA-256 of empty string)
            expected_hash = hashlib.sha256(b"").hexdigest()
            
            self.assertEqual(file_hash, expected_hash)
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)

    def test_known_content_hash(self):
        """Test hash calculation for a file with known content."""
        test_content = b"Hello, Azure Blob Storage!"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_path = Path(temp_file.name)
        
        try:
            # Calculate hash using our function
            file_hash = calculate_file_hash(temp_path)
            
            self.assertEqual(file_hash, expected_hash)
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)

    def test_large_file_hash(self):
        """Test hash calculation for a larger file (1MB)."""
        # Create a 1MB file with repeating pattern
        one_mb = 1024 * 1024
        test_content = b"X" * one_mb
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_path = Path(temp_file.name)
        
        try:
            # Calculate hash using our function
            file_hash = calculate_file_hash(temp_path)
            
            self.assertEqual(file_hash, expected_hash)
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)

    def test_binary_file_hash(self):
        """Test hash calculation for a binary file with null bytes."""
        # Create a file with some binary content including null bytes
        test_content = b"\x00\x01\x02\x03\x04\xFF\xFE\xFD\x00"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_path = Path(temp_file.name)
        
        try:
            # Calculate hash using our function
            file_hash = calculate_file_hash(temp_path)
            
            self.assertEqual(file_hash, expected_hash)
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()