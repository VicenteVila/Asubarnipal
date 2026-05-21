"""Tests for core/stt.py."""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock


class TestSTTModule(unittest.TestCase):
    """Test speech-to-text module functions."""

    def setUp(self):
        """Reset module state."""
        from core import stt
        stt._WHISPER_AVAILABLE = False
        stt._WHISPER_MODEL = None

    def test_transcribe_audio_not_available(self):
        from core import stt

        success, result = stt.transcribe_audio("/tmp/test.ogg")

        self.assertFalse(success)
        self.assertIn("not available", result.lower())

    @patch("core.stt._load_whisper")
    def test_transcribe_audio_success(self, mock_load):
        from core import stt

        mock_load.return_value = True

        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Hello world, this is a test"}
        stt._WHISPER_MODEL = mock_model
        stt._WHISPER_AVAILABLE = True

        success, result = stt.transcribe_audio("/tmp/test.ogg")

        self.assertTrue(success)
        self.assertEqual(result, "Hello world, this is a test")

    @patch("core.stt._load_whisper")
    def test_transcribe_audio_no_speech(self, mock_load):
        from core import stt

        mock_load.return_value = True

        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": ""}
        stt._WHISPER_MODEL = mock_model
        stt._WHISPER_AVAILABLE = True

        success, result = stt.transcribe_audio("/tmp/test.ogg")

        self.assertFalse(success)
        self.assertIn("No speech", result)

    @patch("core.stt._load_whisper")
    def test_transcribe_audio_exception(self, mock_load):
        from core import stt

        mock_load.return_value = True

        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Model error")
        stt._WHISPER_MODEL = mock_model
        stt._WHISPER_AVAILABLE = True

        success, result = stt.transcribe_audio("/tmp/test.ogg")

        self.assertFalse(success)
        self.assertIn("error", result.lower())

    def test_transcribe_ogg_file_not_found(self):
        from core import stt

        success, result = stt.transcribe_ogg("/nonexistent/file.ogg")

        self.assertFalse(success)
        self.assertIn("not found", result.lower())

    @patch("core.stt.transcribe_audio")
    @patch("os.path.exists")
    def test_transcribe_ogg_success(self, mock_exists, mock_transcribe):
        from core import stt

        mock_exists.return_value = True
        mock_transcribe.return_value = (True, "Transcribed text")

        success, result = stt.transcribe_ogg("/tmp/test.ogg")

        self.assertTrue(success)
        mock_transcribe.assert_called_once_with("/tmp/test.ogg")


if __name__ == "__main__":
    unittest.main()
