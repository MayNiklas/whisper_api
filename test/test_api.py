import os
import time
import unittest

import httpx
import torch
from fastapi.testclient import TestClient
from typing import Tuple

from whisper_api import app

"""
Test that the API works.
"""


# remove the comment to run the tests against a local server
# os.environ["test_base_url"] = "http://127.0.0.1:3001"


def do_test() -> Tuple[bool, str]:
    """
    Decide whether to run the tests or not.
    """
    if not torch.cuda.is_available() and (os.environ.get("test_base_url") is None):
        return False, "CUDA is not available and test_base_url is not set"
    return True, ""


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

    do_test, reason = do_test()

    @unittest.skipIf(not do_test, reason)
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

    @unittest.skipIf(not do_test, reason)
    def test_transcribe(self):
        """
        Test that the API can transcribe a given audio file.
        """

        file = open("test/files/En-Open_Source_Software_CD-article.ogg", "rb")
        files = {"file": file}
        response = client.post("/api/v1/transcribe", files=files)
        file.close()

        self.assertEqual(response.status_code, 200)

        print(response.json())

        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = client.get(f"/api/v1/status?task_id={response.json().get("task_id")}")
            if (response.json().get("status")) == "finished":
                break
            print("Waiting for transcription to complete...")
            time.sleep(1)
        else:
            self.fail(f"Transcription did not complete within {timeout} seconds")

        print(response.json())

        self.assertTrue(response.json().get("status") == "finished")
        self.assertTrue(response.json().get("transcript") is not None and len(response.json().get("transcript")) > 0)
