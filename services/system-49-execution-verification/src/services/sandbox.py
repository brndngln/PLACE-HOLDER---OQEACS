"""Sandbox executor — runs code in subprocess-based sandboxes with resource limits."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

import structlog

from src.config import Settings
from src.models import ExecutionResult

logger = structlog.get_logger()


class SandboxExecutor:
    """Execute code in an isolated subprocess with ulimit-based resource constraints."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_tmp = Path(tempfile.gettempdir()) / "omni_sandbox"
        self._base_tmp.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def execute(
        self,
        code: str,
        language: str,
        timeout: int | None = None,
        memory_limit: int | None = None,
        dependencies: list[str] | None = None,
    ) -> ExecutionResult:
        """Execute *code* in *language* and return an ExecutionResult."""
        timeout = timeout or self._settings.EXECUTION_TIMEOUT_SECONDS
        memory_limit = memory_limit or self._settings.MAX_MEMORY_MB

        tmp_dir = Path(tempfile.mkdtemp(dir=self._base_tmp))
        try:
            if dependencies:
                await self._install_deps(dependencies, language, tmp_dir)

            dispatch = {
                "python": self._execute_python,
                "javascript": self._execute_javascript,
                "typescript": self._execute_typescript,
                "bash": self._execute_bash,
            }
            handler = dispatch.get(language)
            if handler is None:
                return ExecutionResult(
                    success=False,
                    stderr=f"Unsupported language: {language}",
                    exit_code=1,
                )
            return await handler(code, tmp_dir, timeout, memory_limit)
        except asyncio.TimeoutError:
            logger.warning("execution_timeout", language=language, timeout=timeout)
            return ExecutionResult(
                success=False,
                stderr=f"Execution timed out after {timeout}s",
                exit_code=124,
            )
        except Exception as exc:
            logger.error("execution_error", error=str(exc), language=language)
            return ExecutionResult(success=False, stderr=str(exc), exit_code=1)
        finally:
            await self._cleanup(tmp_dir)

    # ------------------------------------------------------------------
    # Language-specific executors
    # ------------------------------------------------------------------

    async def _execute_python(
        self, code: str, tmp_dir: Path, timeout: int, memory_limit: int
    ) -> ExecutionResult:
        """Write code to a temp file and run it via Python subprocess."""
        script = tmp_dir / "main.py"
        script.write_text(code, encoding="utf-8")

        memory_bytes = memory_limit * 1024 * 1024
        cmd = (
            f"ulimit -v {memory_bytes} 2>/dev/null; "
            f"ulimit -t {timeout} 2>/dev/null; "
            f"cd {tmp_dir} && python main.py"
        )
        return await self._run_subprocess(cmd, timeout, tmp_dir)

    async def _execute_javascript(
        self, code: str, tmp_dir: Path, timeout: int, memory_limit: int
    ) -> ExecutionResult:
        """Run JavaScript code via Node.js."""
        script = tmp_dir / "main.js"
        script.write_text(code, encoding="utf-8")

        cmd = (
            f"ulimit -v {memory_limit * 1024 * 1024} 2>/dev/null; "
            f"ulimit -t {timeout} 2>/dev/null; "
            f"cd {tmp_dir} && node main.js"
        )
        return await self._run_subprocess(cmd, timeout, tmp_dir)

    async def _execute_typescript(
        self, code: str, tmp_dir: Path, timeout: int, memory_limit: int
    ) -> ExecutionResult:
        """Run TypeScript code via npx tsx."""
        script = tmp_dir / "main.ts"
        script.write_text(code, encoding="utf-8")

        cmd = (
            f"ulimit -v {memory_limit * 1024 * 1024} 2>/dev/null; "
            f"ulimit -t {timeout} 2>/dev/null; "
            f"cd {tmp_dir} && npx tsx main.ts"
        )
        return await self._run_subprocess(cmd, timeout, tmp_dir)

    async def _execute_bash(
        self, code: str, tmp_dir: Path, timeout: int, memory_limit: int
    ) -> ExecutionResult:
        """Run shell script with restricted permissions."""
        script = tmp_dir / "main.sh"
        script.write_text(code, encoding="utf-8")
        script.chmod(0o700)

        cmd = (
            f"ulimit -v {memory_limit * 1024 * 1024} 2>/dev/null; "
            f"ulimit -t {timeout} 2>/dev/null; "
            f"cd {tmp_dir} && bash main.sh"
        )
        return await self._run_subprocess(cmd, timeout, tmp_dir)

    # ------------------------------------------------------------------
    # Dependency installation
    # ------------------------------------------------------------------

    async def _install_deps(
        self, deps: list[str], language: str, tmp_dir: Path
    ) -> None:
        """Install package dependencies into the sandbox temp directory."""
        if not deps:
            return

        if language == "python":
            deps_str = " ".join(deps)
            cmd = f"pip install --target {tmp_dir}/site-packages --quiet {deps_str}"
        elif language in ("javascript", "typescript"):
            deps_str = " ".join(deps)
            cmd = f"cd {tmp_dir} && npm init -y --silent && npm install --silent {deps_str}"
        else:
            logger.info("no_dep_install", language=language)
            return

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(tmp_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            logger.warning(
                "dep_install_failed",
                stderr=stderr.decode(errors="replace")[:500],
                language=language,
            )

    # ------------------------------------------------------------------
    # Subprocess helper
    # ------------------------------------------------------------------

    async def _run_subprocess(
        self, cmd: str, timeout: int, cwd: Path
    ) -> ExecutionResult:
        """Run a shell command and capture all metrics."""
        env = os.environ.copy()
        # Add site-packages from dep installation to PYTHONPATH
        site_packages = cwd / "site-packages"
        if site_packages.exists():
            env["PYTHONPATH"] = str(site_packages)

        start = time.monotonic()
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Process killed after {timeout}s timeout",
                exit_code=124,
                execution_time_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        stdout_str = stdout_bytes.decode(errors="replace")[:50_000]
        stderr_str = stderr_bytes.decode(errors="replace")[:50_000]
        exit_code = proc.returncode or 0

        return ExecutionResult(
            success=exit_code == 0,
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=exit_code,
            execution_time_ms=round(elapsed, 2),
            memory_usage_mb=0.0,  # populated by ResourceMonitor when available
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _cleanup(self, tmp_dir: Path) -> None:
        """Securely remove the sandbox temp directory."""
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
                logger.debug("sandbox_cleaned", path=str(tmp_dir))
        except Exception as exc:
            logger.warning("cleanup_failed", path=str(tmp_dir), error=str(exc))
