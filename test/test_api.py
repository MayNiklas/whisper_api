import time
import unittest
from multiprocessing import Process
from typing import Tuple

import httpx
import uvicorn

from whisper_api import app

"""
Test that the API works.
"""


def do_test() -> Tuple[bool, str]:
    """
    Decide whether to run the tests or not.
    """
    return False, "This tests are currently disabled"


def run_server():
    uvicorn.run(app, port=10291)


class TestAPI(unittest.TestCase):
    """
    Test basic features of the API.
    """

    do_test, reason = do_test()

    proc = Process(target=run_server, args=(), daemon=False)
    client = httpx.Client(base_url="http://127.0.0.1:10291")

    @classmethod
    def setUpClass(cls):
        cls.proc.start()

    @classmethod
    def tearDownClass(cls):
        cls.proc.kill()

    @unittest.skipIf(not do_test, reason)
    def test_loaded_model(self):
        """
        Test that the API is reachable and the model is loaded within 120 seconds.
        """

        time.sleep(5)

        timeout = 120
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = self.client.get("/api/v1/decoder_status")
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
        response = self.client.post("/api/v1/transcribe", files=files)
        file.close()

        self.assertEqual(response.status_code, 200)

        print(response.json())

        timeout = 60
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = self.client.get(f"/api/v1/status?task_id={response.json().get("task_id")}")
            if (response.json().get("status")) == "finished":
                break
            print("Waiting for transcription to complete...")
            time.sleep(1)
        else:
            self.fail(f"Transcription did not complete within {timeout} seconds")
            return False

        print(response.json())

        self.assertTrue(response.json().get("status") == "finished")
        self.assertTrue(response.json().get("transcript") is not None and len(response.json().get("transcript")) > 0)

    @unittest.skipIf(not do_test, reason)
    def test_stability(self):
        """
        Test the stability of the API by running test_transcribe 20 times.
        """

        for i in range(20):
            print(f"Test {i+1}:")
            if self.test_transcribe() is False:
                self.fail("Stability test failed")
