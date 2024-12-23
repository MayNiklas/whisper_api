import time
import unittest

import torch
from fastapi.testclient import TestClient

from whisper_api import app

"""
Test that the API works.
"""

client = TestClient(app)


class TestAPI(unittest.TestCase):
    """
    Test basic features of the API.
    """

    @unittest.skipIf(not torch.cuda.is_available(), "no gpu on this system")
    def test_loaded_model(self):
        """
        Test that the API is reachable and the model is loaded within 120 seconds.
        """
        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = client.get("/api/v1/decoder_status")
            if response.json().get("is_model_loaded") == True:
                break
            print("Waiting for model to load...")
            time.sleep(1)
        else:
            self.fail(f"Model did not load within {timeout} seconds")

        self.assertTrue(response.json().get("is_model_loaded"))
