import pytest


def test_import_whisper_api():
    try:
        import whisper_api
        assert whisper_api
    except ImportError:
        pytest.fail("Failed to import whisper_api")
