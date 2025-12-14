import unittest


class TestImport(unittest.TestCase):

    def test_import_whisper_api(self):
        try:
            import whisper_api

            assert whisper_api
        except ImportError:
            unittest.fail("Failed to 'import whisper_api'")

    def test_from_import(self):
        try:
            from whisper_api import app

            assert app

        except ImportError:
            unittest.fail("Failed to 'from whisper_api import app'")

    # TODO: write a test that attempt to import from a a mp.Process and assert that app does not exist