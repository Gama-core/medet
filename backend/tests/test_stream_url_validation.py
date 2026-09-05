import unittest

from routers.stream import _is_local_stream_url


class StreamUrlValidationTest(unittest.TestCase):
    def test_rejects_loopback_stream_urls(self):
        self.assertTrue(_is_local_stream_url("rtsp://127.0.0.1:8554/mystream"))
        self.assertTrue(_is_local_stream_url("rtsp://localhost:8554/mystream"))
        self.assertTrue(_is_local_stream_url("rtsp://0.0.0.0:8554/mystream"))

    def test_allows_non_loopback_stream_urls(self):
        self.assertFalse(_is_local_stream_url("rtsp://camera.local:8554/mystream"))
        self.assertFalse(_is_local_stream_url("http://192.168.1.42:8080/stream"))


if __name__ == "__main__":
    unittest.main()
