import os
import time
import unittest

import httpx
import torch
from fastapi.testclient import TestClient

from whisper_api import app

"""
Test that the API works.
"""


# if env test_base_url is set, use that as the base url
# export test_base_url=http://127.0.0.1:3001
if os.environ.get("test_base_url") is not None:
    client = httpx.Client(base_url=os.environ.get("test_base_url"))
else:
    client = TestClient(app)


class TestAPI(unittest.TestCase):
    """
    Test basic features of the API.
    """

    @unittest.skipIf(
        (not torch.cuda.is_available() and (os.environ.get("test_base_url") is None)),
        "no gpu on this system and test_base_url not set",
    )
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
