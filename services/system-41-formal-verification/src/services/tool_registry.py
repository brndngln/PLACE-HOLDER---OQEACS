"""Verification tool registry — maps languages to verification backends."""
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.config import Settings
from src.models import (
    CounterExample,
    ToolInfo,
    VerificationResult,
    VerificationStatus,
    VerificationTool,
)

logger = structlog.get_logger()

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "tla_plus": {
        "binary": "/usr/local/lib/tla2tools.jar",
        "command_template": "java -jar /usr/local/lib/tla2tools.jar -config {config} {spec}",
        "purpose": "Distributed protocol verification (deadlock, liveness, safety)",
        "input_ext": ".tla",
        "languages": ["protocol", "distributed"],
    },
    "cbmc": {
        "binary": "/usr/bin/cbmc",
        "command_template": "cbmc --bounds-check --pointer-check --unwind {depth} {source}",
        "purpose": "C/C++ bounded model checking (memory safety, buffer overflows)",
        "input_ext": ".c",
        "languages": ["c", "cpp"],
    },
    "dafny": {
        "binary": "/usr/local/bin/dafny",
        "command_template": "dafny verify {source}",
        "purpose": "Algorithm correctness proofs (pre/post conditions, loop invariants)",
        "input_ext": ".dfy",
        "languages": ["dafny"],
    },
    "spin": {
        "binary": "/usr/bin/spin",
        "command_template": "spin -a {source}",
        "purpose": "Concurrent protocol verification (deadlock freedom, liveness)",
        "input_ext": ".pml",
        "languages": ["protocol", "concurrent"],
    },
    "crosshair": {
        "binary": "/usr/local/bin/crosshair",
        "command_template": "crosshair check {source}",
        "purpose": "Python symbolic execution (finds inputs that violate contracts)",
        "input_ext": ".py",
        "languages": ["python"],
    },
    "kani": {
        "binary": "/usr/local/bin/kani",
        "command_template": "kani {source}",
        "purpose": "Rust formal verification via bounded model checking",
        "input_ext": ".rs",
        "languages": ["rust"],
    },
    "alloy": {
        "binary": "/usr/local/lib/alloy.jar",
        "command_template": "java -jar /usr/local/lib/alloy.jar -c {source}",
        "purpose": "Relational modeling and constraint analysis",
        "input_ext": ".als",
        "languages": ["alloy"],
    },
}

LANGUAGE_TO_TOOL: dict[str, str] = {
    "python": "crosshair",
    "c": "cbmc",
    "cpp": "cbmc",
    "rust": "kani",
    "dafny": "dafny",
    "protocol": "tla_plus",
    "distributed": "tla_plus",
    "concurrent": "spin",
    "alloy": "alloy",
}


def select_tool(language: str, tool_override: VerificationTool | None = None) -> str:
    """Select the best verification tool for a given language."""
    if tool_override is not None:
        return tool_override.value
    tool_id = LANGUAGE_TO_TOOL.get(language)
    if tool_id is None:
        raise ValueError(f"No verification tool available for language: {language}")
    return tool_id


def check_tool_availability(tool_id: str) -> bool:
    """Check if a verification tool binary is available."""
    defn = TOOL_DEFINITIONS.get(tool_id)
    if defn is None:
        return False
    binary = defn["binary"]
    if binary.endswith(".jar"):
        return os.path.isfile(binary)
    return os.path.isfile(binary) and os.access(binary, os.X_OK)


def list_tools() -> list[ToolInfo]:
    """List all available verification tools."""
    tools: list[ToolInfo] = []
    for tool_id, defn in TOOL_DEFINITIONS.items():
        tools.append(
            ToolInfo(
                name=tool_id.replace("_", " ").title(),
                tool_id=VerificationTool(tool_id),
                purpose=defn["purpose"],
                supported_languages=defn["languages"],
                available=check_tool_availability(tool_id),
            )
        )
    return tools


async def run_verification(
    tool_id: str,
    source_code: str,
    properties: list[str],
    settings: Settings,
    depth: int = 100,
) -> VerificationResult:
    """Execute a verification tool against source code."""
    defn = TOOL_DEFINITIONS.get(tool_id)
    if defn is None:
        return VerificationResult(
            id=str(uuid.uuid4()),
            status=VerificationStatus.ERROR,
            tool=VerificationTool(tool_id),
            language="unknown",
            properties_checked=properties,
            properties_passed=[],
            properties_failed=properties,
            stderr=f"Unknown tool: {tool_id}",
        )

    result_id = str(uuid.uuid4())
    work_dir = Path(settings.WORK_DIR) / result_id
    work_dir.mkdir(parents=True, exist_ok=True)

    ext = defn["input_ext"]
    source_file = work_dir / f"source{ext}"
    source_file.write_text(source_code)

    command = defn["command_template"].format(
        source=str(source_file),
        config=str(work_dir / "config.cfg"),
        depth=depth,
    )

    start_time = datetime.utcnow()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=settings.VERIFICATION_TIMEOUT_SECONDS
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if proc.returncode == 0:
            status = VerificationStatus.PASSED
            passed = properties
            failed: list[str] = []
            counterexamples: list[CounterExample] = []
        else:
            status = VerificationStatus.FAILED
            passed = []
            failed = properties
            counterexamples = _parse_counterexamples(stdout + stderr, properties)

        logger.info(
            "verification_complete",
            result_id=result_id,
            tool=tool_id,
            status=status.value,
            elapsed_ms=elapsed_ms,
        )

        return VerificationResult(
            id=result_id,
            status=status,
            tool=VerificationTool(tool_id),
            language=defn["languages"][0],
            properties_checked=properties,
            properties_passed=passed,
            properties_failed=failed,
            counterexamples=counterexamples,
            stdout=stdout[:10000],
            stderr=stderr[:10000],
            execution_time_ms=elapsed_ms,
            completed_at=datetime.utcnow(),
        )

    except asyncio.TimeoutError:
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.warning("verification_timeout", result_id=result_id, tool=tool_id)
        return VerificationResult(
            id=result_id,
            status=VerificationStatus.TIMEOUT,
            tool=VerificationTool(tool_id),
            language=defn["languages"][0],
            properties_checked=properties,
            properties_passed=[],
            properties_failed=properties,
            stderr=f"Verification timed out after {settings.VERIFICATION_TIMEOUT_SECONDS}s",
            execution_time_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.error("verification_error", result_id=result_id, error=str(exc))
        return VerificationResult(
            id=result_id,
            status=VerificationStatus.ERROR,
            tool=VerificationTool(tool_id),
            language=defn["languages"][0],
            properties_checked=properties,
            properties_passed=[],
            properties_failed=[],
            stderr=str(exc),
            execution_time_ms=elapsed_ms,
        )


def _parse_counterexamples(output: str, properties: list[str]) -> list[CounterExample]:
    """Parse counterexamples from tool output."""
    counterexamples: list[CounterExample] = []
    lines = output.splitlines()
    trace_lines: list[str] = []
    in_trace = False

    for line in lines:
        lower = line.lower()
        if "counterexample" in lower or "violation" in lower or "error" in lower:
            in_trace = True
            trace_lines = [line]
        elif in_trace:
            if line.strip() == "" and trace_lines:
                prop_name = properties[0] if properties else "unknown"
                counterexamples.append(
                    CounterExample(
                        property_name=prop_name,
                        description=trace_lines[0] if trace_lines else "Counterexample found",
                        trace=trace_lines,
                    )
                )
                in_trace = False
                trace_lines = []
            else:
                trace_lines.append(line)

    if in_trace and trace_lines:
        prop_name = properties[0] if properties else "unknown"
        counterexamples.append(
            CounterExample(
                property_name=prop_name,
                description=trace_lines[0],
                trace=trace_lines,
            )
        )

    return counterexamples
