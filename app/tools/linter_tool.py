
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool


DOCKER_IMAGE = "code-review-linter:latest"
CONTAINER_FILE = "/workspace/review_code.py"


def run_docker_linter(command: list[str], host_directory: str) -> str:
    """Run a linting command inside a restricted Docker container."""

    docker_command = [
        "docker",
        "run",
        "--rm",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--memory", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "10001:10001",
        "--env", "BLACK_CACHE_DIR=/tmp/black-cache",
        "--mount",
        f"type=bind,source={host_directory},target=/workspace,readonly",
        DOCKER_IMAGE,
        *command,
    ]

    result = subprocess.run(
        docker_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return (
        f"Command: {' '.join(command)}\n"
        f"Exit code: {result.returncode}\n"
        f"Output:\n{result.stdout}\n"
        f"Errors:\n{result.stderr}"
    )


@tool
def run_linter_tool(code_string: str) -> str:
    """
    Analyze Python code using Flake8 and Black inside
    a restricted Docker container.
    """

    if not shutil.which("docker"):
        return "Linting failed: Docker CLI is not installed or not available in PATH."

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "review_code.py"

            file_path.write_text(
                code_string,
                encoding="utf-8",
            )

            commands = [
                ["flake8", CONTAINER_FILE],
                ["black", "--check", CONTAINER_FILE],
            ]

            results = []

            for command in commands:
                results.append(
                    run_docker_linter(command, temp_dir)
                )

            return "\n\n".join(results)

    except subprocess.TimeoutExpired:
        return "Linting failed: Docker linting timed out."

    except Exception as error:
        return f"Linting failed: {str(error)}"
