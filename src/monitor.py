"""System resource and decompression performance monitoring.

Provides real-time tracking of:
- RAM resident set size (RSS) and peak memory
- CPU user and system time, and CPU % load
- Decompression streaming progress, file counts, byte rates
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

try:
    import resource
except ImportError:
    resource = None  # Windows compatibility fallback


def get_ram_rss_mb() -> float:
    """Return the current resident memory (RSS) in megabytes."""
    # On Linux, /proc/self/status provides exact live VmRSS
    if os.path.exists("/proc/self/status"):
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024.0
        except Exception:
            pass

    if resource:
        try:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            # macOS ru_maxrss is in bytes, Linux is in KiB
            scale = 1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0
            return ru.ru_maxrss / scale
        except Exception:
            pass
    return 0.0


def get_peak_ram_mb() -> float:
    """Return the maximum peak memory (Max RSS) in megabytes since process start."""
    if os.path.exists("/proc/self/status"):
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmPeak:"):
                        return int(line.split()[1]) / 1024.0
        except Exception:
            pass

    if resource:
        try:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            scale = 1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0
            return ru.ru_maxrss / scale
        except Exception:
            pass
    return 0.0


def get_cpu_times() -> tuple[float, float]:
    """Return (cpu_user_seconds, cpu_system_seconds)."""
    if resource:
        try:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            return ru.ru_utime, ru.ru_stime
        except Exception:
            pass
    return time.process_time(), 0.0


class ResourceSnapshot:
    """A point-in-time snapshot of system and process resource usage."""

    def __init__(self) -> None:
        self.wall_time = time.perf_counter()
        self.user_time, self.sys_time = get_cpu_times()
        self.ram_rss_mb = get_ram_rss_mb()
        self.peak_ram_mb = get_peak_ram_mb()

    def diff(self, start: ResourceSnapshot) -> dict[str, Any]:
        """Compute delta between this snapshot and an earlier start snapshot."""
        dt = max(self.wall_time - start.wall_time, 1e-6)
        du = max(self.user_time - start.user_time, 0.0)
        ds = max(self.sys_time - start.sys_time, 0.0)
        cpu_pct = min(100.0 * (du + ds) / dt, 100.0 * (os.cpu_count() or 1))
        return {
            "elapsed_s": dt,
            "cpu_user_s": du,
            "cpu_sys_s": ds,
            "cpu_percent": cpu_pct,
            "ram_rss_mb": self.ram_rss_mb,
            "peak_ram_mb": max(self.peak_ram_mb, start.peak_ram_mb),
        }


class PerformanceTracker:
    """Tracks performance and resource usage across multi-step pipelines."""

    def __init__(self, operation_name: str = "Operation") -> None:
        self.operation_name = operation_name
        self.start_snapshot = ResourceSnapshot()
        self.step_snapshots: dict[str, ResourceSnapshot] = {}

    def mark_step(self, step_name: str) -> dict[str, Any]:
        """Mark completion of a pipeline step and return step delta metrics."""
        now = ResourceSnapshot()
        last = list(self.step_snapshots.values())[-1] if self.step_snapshots else self.start_snapshot
        delta = now.diff(last)
        self.step_snapshots[step_name] = now
        return delta

    def finish(self) -> dict[str, Any]:
        """Complete tracking and return total metrics."""
        now = ResourceSnapshot()
        return now.diff(self.start_snapshot)

    @staticmethod
    def format_summary(metrics: dict[str, Any]) -> str:
        """Format metrics into a concise human-readable summary string."""
        elapsed = metrics.get("elapsed_s", 0.0)
        user_s = metrics.get("cpu_user_s", 0.0)
        sys_s = metrics.get("cpu_sys_s", 0.0)
        cpu_pct = metrics.get("cpu_percent", 0.0)
        ram = metrics.get("ram_rss_mb", 0.0)
        peak = metrics.get("peak_ram_mb", 0.0)

        time_str = f"{elapsed * 1000:.0f}ms" if elapsed < 1.0 else f"{elapsed:.2f}s"
        return (
            f"RAM: {ram:.1f} Mo (pic: {peak:.1f} Mo) | "
            f"CPU user: {user_s:.2f}s (sys: {sys_s:.2f}s, {cpu_pct:.1f}%) | "
            f"Durée: {time_str}"
        )
