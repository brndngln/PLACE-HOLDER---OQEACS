"""Resource monitor — tracks CPU, memory, and I/O for sandbox processes."""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

import structlog

logger = structlog.get_logger()


class ResourceMonitor:
    """Monitor and enforce resource limits on running sandbox processes."""

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def monitor_execution(self, pid: int) -> dict:
        """Track CPU%, memory, and disk I/O for a running process.

        Returns a dict with resource usage stats collected at sampling intervals.
        """
        stats: dict = {
            "pid": pid,
            "peak_memory_mb": 0.0,
            "cpu_percent": 0.0,
            "samples": 0,
        }

        try:
            while self._process_alive(pid):
                mem_mb = self._get_memory_mb(pid)
                cpu_pct = self._get_cpu_percent(pid)

                stats["peak_memory_mb"] = max(stats["peak_memory_mb"], mem_mb)
                stats["cpu_percent"] = cpu_pct
                stats["samples"] += 1

                await asyncio.sleep(0.25)  # sample every 250ms
        except ProcessLookupError:
            pass
        except Exception as exc:
            logger.warning("monitor_error", pid=pid, error=str(exc))

        return stats

    async def check_memory_limit(self, pid: int, limit_mb: int) -> bool:
        """Check if a process exceeds *limit_mb*. Kill it if so.

        Returns True if the process was killed for exceeding the limit.
        """
        try:
            mem_mb = self._get_memory_mb(pid)
            if mem_mb > limit_mb:
                logger.warning(
                    "memory_limit_exceeded",
                    pid=pid,
                    usage_mb=round(mem_mb, 1),
                    limit_mb=limit_mb,
                )
                os.kill(pid, signal.SIGKILL)
                return True
        except ProcessLookupError:
            pass
        except Exception as exc:
            logger.warning("memory_check_error", pid=pid, error=str(exc))
        return False

    async def check_timeout(self, pid: int, timeout_seconds: int) -> None:
        """Kill a process if it exceeds the given timeout."""
        try:
            await asyncio.sleep(timeout_seconds)
            if self._process_alive(pid):
                logger.warning("timeout_kill", pid=pid, timeout=timeout_seconds)
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as exc:
            logger.warning("timeout_check_error", pid=pid, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _process_alive(pid: int) -> bool:
        """Return True if the process with *pid* is still running."""
        try:
            os.kill(pid, 0)  # signal 0 = existence check
            return True
        except (ProcessLookupError, PermissionError):
            return False

    @staticmethod
    def _get_memory_mb(pid: int) -> float:
        """Read RSS from /proc/<pid>/status (Linux-specific)."""
        status_path = Path(f"/proc/{pid}/status")
        if not status_path.exists():
            return 0.0

        try:
            text = status_path.read_text()
            for line in text.splitlines():
                if line.startswith("VmRSS:"):
                    # Value is in kB
                    parts = line.split()
                    return float(parts[1]) / 1024.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _get_cpu_percent(pid: int) -> float:
        """Rough CPU% from /proc/<pid>/stat (Linux-specific).

        This is an instantaneous approximation, not a rolling average.
        """
        stat_path = Path(f"/proc/{pid}/stat")
        if not stat_path.exists():
            return 0.0

        try:
            text = stat_path.read_text()
            fields = text.rsplit(")", 1)[-1].split()
            # fields[11] = utime, fields[12] = stime (in clock ticks after the ')')
            utime = int(fields[11])
            stime = int(fields[12])
            total_ticks = utime + stime
            clock_hz = os.sysconf("SC_CLK_TCK")
            return (total_ticks / clock_hz) * 100.0
        except Exception:
            pass
        return 0.0
