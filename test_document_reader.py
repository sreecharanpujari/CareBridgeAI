import unittest
import io
from modules.document_reader import (
    validate_uploaded_file,
    extract_text_from_pdf,
    extract_text_from_image,
    MAX_FILE_SIZE_MB
)

class DummyUpload:
    def __init__(self, name, size):
        self.name = name
        self.size = size

class TestDocumentReader(unittest.TestCase):

    def test_file_validation_valid_pdf(self):
        file = DummyUpload("discharge_note.pdf", 1024 * 500) # 500 KB
        is_valid, msg = validate_uploaded_file(file)
        self.assertTrue(is_valid)

    def test_file_validation_invalid_type(self):
        file = DummyUpload("virus.exe", 1024)
        is_valid, msg = validate_uploaded_file(file)
        self.assertFalse(is_valid)
        self.assertIn("Unsupported file type", msg)

    def test_file_validation_oversized(self):
        file = DummyUpload("huge_file.pdf", (MAX_FILE_SIZE_MB + 5) * 1024 * 1024)
        is_valid, msg = validate_uploaded_file(file)
        self.assertFalse(is_valid)
        self.assertIn("too large", msg)

    def test_empty_pdf_handling(self):
        # Empty byte stream should be caught gracefully without crashing
        text, success, msg = extract_text_from_pdf(b"")
        self.assertFalse(success)
        self.assertIn("Error", msg)

    def test_unreadable_image_handling(self):
        # Random non-image bytes should not crash the app
        text, success, msg = extract_text_from_image(b"not-an-image")
        self.assertFalse(success)
        self.assertIn("Invalid or unreadable image", msg)

if __name__ == "__main__":
    unittest.main()

