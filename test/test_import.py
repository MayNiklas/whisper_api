import unittest


class TestImport(unittest.TestCase):

    def test_import_whisper_api(self):
        try:
            import whisper_api
            assert whisper_api
        except ImportError:
            unittest.fail("Failed to import whisper_api")
