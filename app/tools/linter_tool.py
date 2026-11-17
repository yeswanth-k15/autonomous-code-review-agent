
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool


@tool
def run_linter_tool(code_string: str) -> str:
    """
    Analyze Python code using Flake8 and Black.

    Writes code to a temporary file and executes
    linting tools with a timeout.
    """

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            file_path = Path(temp_dir) / "review_code.py"

            file_path.write_text(
                code_string,
                encoding="utf-8"
            )

            results = []

            commands = [
                ["flake8", str(file_path)],
                ["black", "--check", str(file_path)]
            ]

            for command in commands:

                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False
                )

                results.append(
                    f"Command: {' '.join(command)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Output:\n{result.stdout}\n"
                    f"Errors:\n{result.stderr}"
                )

            return "\n\n".join(results)

    except subprocess.TimeoutExpired:
        return "Linting failed: execution timed out."

    except Exception as error:
        return f"Linting failed: {str(error)}"
