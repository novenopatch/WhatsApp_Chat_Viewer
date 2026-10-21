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
    """Return the current resident memory (RSS) in megabytes.

    Reads RSS from /proc/self/status on Linux, or uses resource.getrusage()
    on other platforms (macOS, Unix). RSS represents the actual physical
    memory used by the process, excluding swap.

    Returns:
        RSS value in megabytes, or 0.0 if unavailable.

    Note:
        On macOS, ru_maxrss is in bytes; on Linux, it's in KiB.
    """
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
    """Return the maximum peak memory (Max RSS) in megabytes since process start.

    Reads VmPeak from /proc/self/status on Linux, or uses resource.getrusage()
    on other platforms. Peak memory represents the highest RSS value recorded
    during the process lifetime.

    Returns:
        Peak RSS value in megabytes, or 0.0 if unavailable.

    Note:
        On platforms without VmPeak support, returns current RSS instead.
    """
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
    """Return (cpu_user_seconds, cpu_system_seconds).

    CPU time represents the actual CPU time consumed by the process:
    - User time: Time spent in user-mode code
    - System time: Time spent in kernel-mode code

    Returns:
        Tuple of (user_seconds, system_seconds). Returns (process_time(), 0.0)
        if resource module is unavailable.

    Note:
        User + system time can exceed wall-clock time on multi-core systems.
    """
    if resource:
        try:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            return ru.ru_utime, ru.ru_stime
        except Exception:
            pass
    return time.process_time(), 0.0


class ResourceSnapshot:
    """A point-in-time snapshot of system and process resource usage.

    Captures current state of CPU time, memory usage, and wall-clock time.
    Used to compute deltas between two points in time.

    Attributes:
        wall_time: High-resolution wall-clock time (seconds).
        user_time: CPU user time consumed (seconds).
        sys_time: CPU system time consumed (seconds).
        ram_rss_mb: Current RSS memory usage (megabytes).
        peak_ram_mb: Peak RSS memory usage (megabytes).
    """

    def __init__(self) -> None:
        """Create a new resource snapshot with current values."""
        self.wall_time = time.perf_counter()
        self.user_time, self.sys_time = get_cpu_times()
        self.ram_rss_mb = get_ram_rss_mb()
        self.peak_ram_mb = get_peak_ram_mb()

    def diff(self, start: ResourceSnapshot) -> dict[str, Any]:
        """Compute delta between this snapshot and an earlier start snapshot.

        Args:
            start: Earlier ResourceSnapshot to compare against.

        Returns:
            Dictionary with keys:
            - elapsed_s: Wall-clock time elapsed (seconds)
            - cpu_user_s: CPU user time consumed (seconds)
            - cpu_sys_s: CPU system time consumed (seconds)
            - cpu_percent: CPU utilization percentage (0-100 * cpu_count)
            - ram_rss_mb: Current RSS at this snapshot (megabytes)
            - peak_ram_mb: Peak RSS across both snapshots (megabytes)
        """
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
    """Tracks performance and resource usage across multi-step pipelines.

    Records resource snapshots at operation start, at each step, and at finish.
    Useful for profiling complex operations like ZIP extraction, parsing, and rendering.

    Attributes:
        operation_name: Human-readable name for the tracked operation.
        start_snapshot: ResourceSnapshot taken at initialization.
        step_snapshots: Dict mapping step names to their ResourceSnapshots.
    """

    def __init__(self, operation_name: str = "Operation") -> None:
        """Initialize performance tracking for an operation.

        Args:
            operation_name: Human-readable name for the operation.
        """
        self.operation_name = operation_name
        self.start_snapshot = ResourceSnapshot()
        self.step_snapshots: dict[str, ResourceSnapshot] = {}

    def mark_step(self, step_name: str) -> dict[str, Any]:
        """Mark completion of a pipeline step and return step delta metrics.

        Takes a new snapshot and computes delta from the previous snapshot
        (or start snapshot if this is the first step).

        Args:
            step_name: Name/label for the completed step.

        Returns:
            Dictionary with delta metrics (elapsed time, CPU, RAM, etc.).
        """
        now = ResourceSnapshot()
        last = list(self.step_snapshots.values())[-1] if self.step_snapshots else self.start_snapshot
        delta = now.diff(last)
        self.step_snapshots[step_name] = now
        return delta

    def finish(self) -> dict[str, Any]:
        """Complete tracking and return total metrics.

        Takes a final snapshot and computes delta from the start snapshot.

        Returns:
            Dictionary with total operation metrics from start to finish.
        """
        now = ResourceSnapshot()
        return now.diff(self.start_snapshot)

    @staticmethod
    def format_summary(metrics: dict[str, Any]) -> str:
        """Format metrics into a concise human-readable summary string.

        Args:
            metrics: Dictionary from diff() or finish() with performance metrics.

        Returns:
            Formatted string like "RAM: 45.2 Mo (pic: 52.1 Mo) | CPU user: 1.23s (sys: 0.45s, 34.2%) | Durée: 3.45s"
        """
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
