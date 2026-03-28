import socket
import time
import unittest
from multiprocessing import Process
from pathlib import Path
from typing import Optional

import httpx
import uvicorn

from whisper_api import app

"""
Test that the API works.
"""

TEST_FILES_DIR = Path(__file__).parent / "files"
TEST_AUDIO_FILE = TEST_FILES_DIR / "En-Open_Source_Software_CD-article.ogg"


def do_test() -> tuple[bool, str]:
    """
    Decide whether to run the tests or not.
    These tests require a running whisper model and are skipped by default.
    """
    return True, "These tests require a whisper model and are skipped by default"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run_server(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port)


class TestAPI(unittest.TestCase):
    """
    Test basic features of the API.
    """

    do_test, reason = do_test()

    POST_TIMEOUT_S = 30
    STATUS_REQUEST_TIMEOUT_S = 10
    TRANSCRIPTION_DEADLINE_S = 240
    STABILITY_RUNS = 20

    proc: Optional[Process] = None
    client: Optional[httpx.Client] = None
    server_port: Optional[int] = None

    @classmethod
    def setUpClass(cls):
        cls.server_port = find_free_port()
        cls.client = httpx.Client(base_url=f"http://127.0.0.1:{cls.server_port}")
        cls.proc = Process(target=run_server, args=(cls.server_port,), daemon=False)
        cls.proc.start()

        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = cls.client.get("/api/v1/decoder_status", timeout=2)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)

        cls.tearDownClass()
        raise RuntimeError("Server did not become ready in setUpClass")

    @classmethod
    def tearDownClass(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None

        if cls.proc is None:
            return

        if cls.proc.is_alive():
            cls.proc.terminate()
            cls.proc.join(timeout=5)

        if cls.proc.is_alive():
            cls.proc.kill()
            cls.proc.join(timeout=5)

        cls.proc = None
        cls.server_port = None

    @unittest.skipIf(not do_test, reason)
    def test_version(self):
        """Test that the version endpoint returns a version string."""
        response = self.client.get("/api/v1/version")
        self.assertEqual(response.status_code, 200)
        self.assertIn("version", response.json())

    @unittest.skipIf(not do_test, reason)
    def test_loaded_model(self):
        """
        Test that the API is reachable and the model is loaded within 120 seconds.
        """
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
    def test_status_invalid_task_id(self):
        """Test that requesting status for an unknown task_id returns 400."""
        response = self.client.get("/api/v1/status?task_id=00000000000000000000000000000000")
        self.assertEqual(response.status_code, 400)

    @unittest.skipIf(not do_test, reason)
    def test_transcribe_non_audio_file(self):
        """Test that uploading a non-audio file returns 400."""
        files = {"file": ("test.txt", b"this is not audio", "text/plain")}
        response = self.client.post("/api/v1/transcribe", files=files, timeout=self.POST_TIMEOUT_S)
        self.assertEqual(response.status_code, 400)

    @unittest.skipIf(not do_test, reason)
    def test_transcribe(self):
        """
        Test that the API can transcribe a given audio file.
        """
        result = self._run_transcription_and_wait()

        self.assertEqual(result.get("status"), "finished")
        self.assertTrue(result.get("transcript") is not None and len(result.get("transcript")) > 0)

    @unittest.skipIf(not do_test, reason)
    def test_translate(self):
        """
        Test that the API can translate a given audio file.
        """
        result = self._run_transcription_and_wait(endpoint="/api/v1/translate")

        self.assertEqual(result.get("status"), "finished")
        self.assertTrue(result.get("transcript") is not None and len(result.get("transcript")) > 0)

    @unittest.skipIf(not do_test, reason)
    def test_stability(self):
        """
        Test the stability of the API by running test_transcribe 20 times.
        """
        for i in range(self.STABILITY_RUNS):
            with self.subTest(run=i + 1):
                result = self._run_transcription_and_wait()
                self.assertEqual(result.get("status"), "finished")
                self.assertTrue(result.get("transcript") is not None and len(result.get("transcript")) > 0)

    def _run_transcription_and_wait(self, endpoint: str = "/api/v1/transcribe") -> dict:
        with open(TEST_AUDIO_FILE, "rb") as file:
            files = {"file": file}
            response = self.client.post(endpoint, files=files, timeout=self.POST_TIMEOUT_S)

        self.assertEqual(response.status_code, 200)
        task_id = response.json().get("task_id")
        self.assertIsNotNone(task_id)

        print(response.json())

        start_time = time.time()

        while time.time() - start_time < self.TRANSCRIPTION_DEADLINE_S:
            try:
                status_response = self.client.get(
                    f"/api/v1/status?task_id={task_id}", timeout=self.STATUS_REQUEST_TIMEOUT_S
                )
            except httpx.TimeoutException:
                # Status requests can occasionally time out under heavy CPU load; retry until deadline.
                print("Status request timed out, retrying...")
                time.sleep(1)
                continue

            self.assertEqual(status_response.status_code, 200)
            payload = status_response.json()

            if payload.get("status") == "finished":
                print(payload)
                return payload

            print("Waiting for transcription to complete...")
            time.sleep(1)

        self.fail(f"Transcription did not complete within {self.TRANSCRIPTION_DEADLINE_S} seconds")
