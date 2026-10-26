import importlib.util
import http.client
from contextlib import closing
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from PIL import Image

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "image_server.py"
spec = importlib.util.spec_from_file_location("image_server", MODULE)
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)


class FixtureServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        server_module.prepare(cls.root, 1, "ALL", 7)
        metadata = json.loads((cls.root / "manifest.json").read_text(encoding="utf-8"))
        cls.prepared_metadata = metadata.copy()
        metadata["count"] = 10
        (cls.root / "manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), server_module.handler(cls.root))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def fetch(self, path):
        with closing(http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)) as connection:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def test_prepare_all_writes_all_sizes_and_encodings(self):
        self.assertEqual(self.prepared_metadata["formats"], ["JPEG", "PNG", "WEBP"])
        self.assertEqual(self.prepared_metadata["version"], 7)
        for w, h in server_module.sizes(1):
            for fmt in server_module.FORMATS:
                with Image.open(self.root / "item1" / f"{w}x{h}.{fmt.lower()}") as image:
                    self.assertEqual(image.size, (w, h))
                    self.assertEqual(image.format, fmt)

    def test_selected_format_matches_actual_bytes_and_mime(self):
        w, h = server_module.sizes(1)[0]
        for fmt in server_module.FORMATS:
            with self.subTest(fmt=fmt):
                status, headers, data = self.fetch(f"/seed/item1/{w}/{h}?format={fmt}&v=1&delay_ms=0")
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Type"], server_module.MIME[fmt])
                self.assertEqual(int(headers["Content-Length"]), len(data))
                with Image.open(io.BytesIO(data)) as image:
                    self.assertEqual(image.format, fmt)
                    self.assertEqual(image.size, (w, h))

    def test_url_version_does_not_change_prepared_content(self):
        w, h = server_module.sizes(1)[0]
        first = self.fetch(f"/seed/item1/{w}/{h}?v=1")
        second = self.fetch(f"/seed/item1/{w}/{h}?v=2")
        self.assertEqual(first[0], 200)
        self.assertEqual(first[2], second[2])
        self.assertEqual(second[1]["X-ImageOpt-Content-Version"], "7")
        self.assertEqual(second[1]["X-ImageOpt-URL-Version"], "2")

    def test_bad_queries_rejected(self):
        w, h = server_module.sizes(1)[0]
        for query in ("format=GIF", "v=0", "v=-1", "v=1000000", "v=one", "delay_ms=60001", "delay_ms=-1", "delay_ms=1.5", "error=2", "format=JPEG&format=PNG", "unknown=1", "v=", "error"):
            with self.subTest(query=query):
                self.assertEqual(self.fetch(f"/seed/item1/{w}/{h}?{query}")[0], 400)

    def test_error_routes_missing_assets_and_invalid_dimensions(self):
        w, h = server_module.sizes(10)[0]
        status, _, body = self.fetch(f"/seed/item10/{w}/{h}?error=1")
        self.assertEqual(status, 404)
        self.assertIn(b"Intentional TC06 error", body)
        for path in ("/error", "/error/item10", f"/seed/item10/{w}/{h}", "/seed/item1/123/456", "/seed/item0/480/720", "/seed/item1001/480/720", "/seed/../manifest.json", "/manifest.json"):
            with self.subTest(path=path):
                self.assertEqual(self.fetch(path)[0], 404)

    def test_delay_is_applied_without_encoding_on_request(self):
        w, h = server_module.sizes(1)[0]
        with patch.object(server_module.time, "sleep") as sleep, patch.object(Image.Image, "save", side_effect=AssertionError("encoding during GET")):
            self.assertEqual(self.fetch(f"/seed/item1/{w}/{h}?delay_ms=60000")[0], 200)
            sleep.assert_called_once_with(60.0)

    def test_default_jpeg_and_legacy_manifest(self):
        w, h = server_module.sizes(1)[0]
        self.assertEqual(self.fetch(f"/seed/item1/{w}/{h}")[1]["Content-Type"], "image/jpeg")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"count": 1, "format": "PNG", "version": 1}), encoding="utf-8")
            self.assertEqual(server_module.read_manifest(root)["formats"], ["PNG"])
            server_module.handler(root, fmt="PNG")
            with self.assertRaises(ValueError):
                server_module.handler(root, fmt="JPEG")

    def test_default_delay_and_query_override(self):
        self.assertEqual(server_module.query_options("", "JPEG", 2.5)[2], 2.5)
        self.assertEqual(server_module.query_options("delay_ms=0", "JPEG", 2.5)[2], 0.0)
        for delay in (float("nan"), float("inf"), -1, 61):
            with self.assertRaises(ValueError):
                server_module.handler(self.root, delay=delay)

    def test_unprepared_format_is_not_silently_substituted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"count": 1, "format": "JPEG", "version": 1}), encoding="utf-8")
            local_server = ThreadingHTTPServer(("127.0.0.1", 0), server_module.handler(root))
            thread = threading.Thread(target=local_server.serve_forever, daemon=True)
            thread.start()
            try:
                with closing(http.client.HTTPConnection("127.0.0.1", local_server.server_port, timeout=5)) as connection:
                    connection.request("GET", "/seed/item1/480/720?format=WEBP")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 404)
                    self.assertIn(b"Format not prepared", response.read())
            finally:
                local_server.shutdown()
                local_server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

