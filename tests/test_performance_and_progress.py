"""Tests for resource monitoring, decompression progress, and ultra-performance features."""

import os
import tempfile
import time
import unittest
import zipfile

from src.config import parse_args
from src.monitor import (
    PerformanceTracker,
    ResourceSnapshot,
    get_cpu_times,
    get_peak_ram_mb,
    get_ram_rss_mb,
)
from src.zip_handler import safe_extract_zip


class TestMonitor(unittest.TestCase):
    """Tests for system resource monitoring and performance tracking."""

    def test_get_ram_metrics(self):
        ram = get_ram_rss_mb()
        peak = get_peak_ram_mb()
        self.assertIsInstance(ram, float)
        self.assertGreaterEqual(ram, 0.0)
        self.assertIsInstance(peak, float)
        self.assertGreaterEqual(peak, 0.0)

    def test_get_cpu_times(self):
        utime, stime = get_cpu_times()
        self.assertIsInstance(utime, float)
        self.assertIsInstance(stime, float)
        self.assertGreaterEqual(utime, 0.0)
        self.assertGreaterEqual(stime, 0.0)

    def test_resource_snapshot_and_tracker(self):
        tracker = PerformanceTracker("TestOperation")
        time.sleep(0.02)
        # perform some CPU activity
        _ = sum(i * i for i in range(50000))

        step_res = tracker.mark_step("step1")
        self.assertIn("elapsed_s", step_res)
        self.assertIn("cpu_user_s", step_res)
        self.assertIn("ram_rss_mb", step_res)
        self.assertGreater(step_res["elapsed_s"], 0)

        summary = tracker.format_summary(step_res)
        self.assertIn("RAM:", summary)
        self.assertIn("CPU user:", summary)

        final = tracker.finish()
        self.assertIn("elapsed_s", final)
        self.assertIn("peak_ram_mb", final)


class TestDecompressionProgress(unittest.TestCase):
    """Tests for zip decompression progress reporting and ultra-perf mode."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.zip_path = os.path.join(self.temp_dir, "test.zip")
        self.extract_dir = os.path.join(self.temp_dir, "extracted")

        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("_chat.txt", "[10/10/2024 10:00:00] Alice: Bonjour !\n")
            zf.writestr("photo1.jpg", b"fake photo data " * 50)
            zf.writestr("photo2.jpg", b"fake photo data 2 " * 50)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_extract_zip_with_progress_callback(self):
        calls = []

        def callback(info):
            calls.append(dict(info))

        extracted = safe_extract_zip(
            self.zip_path,
            self.extract_dir,
            progress_callback=callback,
            ultra_perf=True,
        )

        self.assertEqual(len(extracted), 3)
        self.assertGreaterEqual(len(calls), 3)
        last_call = calls[-1]
        self.assertEqual(last_call["files_extracted"], 3)
        self.assertEqual(last_call["total_files"], 3)
        self.assertEqual(last_call["percent"], 100)


class TestCliFlags(unittest.TestCase):
    """Tests for CLI arguments --verbose and --ultra-perf."""

    def test_parse_args_verbose_and_ultra_perf(self):
        args = parse_args(["--verbose", "--ultra-perf"])
        self.assertTrue(args.verbose)
        self.assertTrue(args.ultra_perf)

        args_short = parse_args(["-v", "--fast"])
        self.assertTrue(args_short.verbose)
        self.assertTrue(args_short.ultra_perf)


if __name__ == "__main__":
    unittest.main()
