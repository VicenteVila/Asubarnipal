"""Tests for core/vision.py."""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock


class TestVisionModule(unittest.TestCase):
    """Test vision module functions."""

    @patch("core.vision.requests.post")
    @patch("builtins.open")
    @patch("os.path.exists")
    def test_analyze_image_success(self, mock_exists, mock_open, mock_post):
        from core.vision import analyze_image

        mock_exists.return_value = True
        mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"data")))
        mock_open.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "A cat sitting on a chair"}
        mock_post.return_value = mock_response

        success, result = analyze_image("/tmp/test.jpg", "Describe this")

        self.assertTrue(success)
        self.assertEqual(result, "A cat sitting on a chair")

    def test_analyze_image_file_not_found(self):
        from core.vision import analyze_image

        success, result = analyze_image("/nonexistent/path.jpg")

        self.assertFalse(success)
        self.assertIn("not found", result.lower())

    @patch("core.vision.requests.post")
    @patch("builtins.open")
    @patch("os.path.exists")
    def test_analyze_image_connection_error(self, mock_exists, mock_open, mock_post):
        from core.vision import analyze_image
        import requests

        mock_exists.return_value = True
        mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"data")))
        mock_open.return_value.__exit__ = Mock(return_value=False)

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        success, result = analyze_image("/tmp/test.jpg")

        self.assertFalse(success)
        self.assertIn("Cannot connect", result)

    @patch("core.vision.requests.get")
    def test_is_vision_available_true(self, mock_get):
        from core.vision import is_vision_available

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llava:7b"}, {"name": "qwen3.5:4b"}]
        }
        mock_get.return_value = mock_response

        self.assertTrue(is_vision_available())

    @patch("core.vision.requests.get")
    def test_is_vision_available_false(self, mock_get):
        from core.vision import is_vision_available

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "qwen3.5:4b"}]}
        mock_get.return_value = mock_response

        self.assertFalse(is_vision_available())

    @patch("core.vision.requests.get")
    def test_is_vision_available_error(self, mock_get):
        from core.vision import is_vision_available

        mock_get.side_effect = Exception("Connection error")

        self.assertFalse(is_vision_available())

    @patch("core.vision.analyze_image")
    def test_analyze_photo_telegram(self, mock_analyze):
        from core.vision import analyze_photo_telegram

        mock_analyze.return_value = (True, "A photo description")

        success, result = analyze_photo_telegram("/tmp/photo.jpg")

        self.assertTrue(success)
        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        self.assertIn("Describe what you see", call_args[1]["prompt"])

    @patch("core.vision.analyze_image")
    def test_extract_text_from_image(self, mock_analyze):
        from core.vision import extract_text_from_image

        mock_analyze.return_value = (True, "Extracted text content")

        success, result = extract_text_from_image("/tmp/photo.jpg")

        self.assertTrue(success)
        call_args = mock_analyze.call_args
        self.assertIn("Extract all text", call_args[1]["prompt"])


if __name__ == "__main__":
    unittest.main()
