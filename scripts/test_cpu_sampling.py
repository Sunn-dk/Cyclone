"""Validate ART method flags, thread attribution and rejection of truncated records."""
import struct
import tempfile
import unittest
from pathlib import Path
from run_cpu_sampling import inspect_trace


class TraceParserTest(unittest.TestCase):
    def test_threads_flags_and_truncation(self):
        text = (b"*version\n3\nclock=dual\n*threads\n1\tmain\n2\tworker\n*methods\n"
                b"0x4\tandroid.graphics.BitmapFactory\tdecodeStream\n"
                b"0x8\tandroid.view.View\tdraw\n*end\n")
        records = b"".join(struct.pack("<HIII", *r) for r in
                           [(1, 8, 100, 100), (2, 4, 200, 200), (2, 5, 700, 800)])
        data = text + struct.pack("<4sHHQH", b"SLOW", 3, 18, 0, 14) + records
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            trace = out / "test.trace"
            trace.write_bytes(data)
            result = inspect_trace(trace, out)
            self.assertEqual(result["records"], 3)
            import csv
            with (out / "cpu_threads.csv").open(encoding="utf-8-sig") as f:
                rows = {r["thread"]: r for r in csv.DictReader(f)}
            self.assertEqual(rows["main"]["bitmap_decode_transition_records"], "0")
            self.assertEqual(rows["worker"]["bitmap_decode_transition_records"], "2")
            self.assertEqual(float(rows["worker"]["observed_cpu_delta_ms"]), 0.5)
            trace.write_bytes(data[:-1])
            with self.assertRaises(AssertionError):
                inspect_trace(trace, out)


if __name__ == "__main__":
    unittest.main()
