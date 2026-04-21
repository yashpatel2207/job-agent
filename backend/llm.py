"""Shell out to the `claude` CLI so calls use the Max subscription instead of a metered API key."""
import os
import shutil
import subprocess
from pathlib import Path


def _find_claude():
    exe = shutil.which("claude.exe")
    if exe:
        return exe
    npm_exe = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if npm_exe.exists():
        return str(npm_exe)
    return shutil.which("claude")


_CLAUDE_BIN = _find_claude()


def call_claude(prompt: str, model: str = "opus", timeout: int = 300) -> str:
    if _CLAUDE_BIN is None:
        raise RuntimeError("`claude` CLI not found on PATH. Install Claude Code and run `claude login`.")

    result = subprocess.run(
        [_CLAUDE_BIN, "-p", "--model", model],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr.strip()}")
    return result.stdout.strip()
