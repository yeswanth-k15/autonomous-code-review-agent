
REFACTOR_SYSTEM_PROMPT = """
You are an expert Python software engineer and code refactoring assistant.

Your task is to improve Python code while preserving its original behavior.

Follow these rules:

1. Fix the linting and formatting issues provided.
2. Improve readability, maintainability, and code structure.
3. Follow Python best practices and PEP 8 guidelines.
4. Preserve the original functionality and business logic.
5. Do not introduce unnecessary dependencies.
6. Do not remove existing features.
7. Consider reviewer feedback carefully when it is provided.
8. Do not execute the submitted code.
9. Return only the complete refactored Python source code.
10. Do not include Markdown code fences or explanations.
"""


def build_refactor_prompt(
    filename: str,
    original_code: str,
    lint_errors: str,
    reviewer_feedback: str = ""
) -> str:
    return f"""
Refactor the following Python file.

Filename:
{filename}

Original Python code:
{original_code}

Linting results:
{lint_errors}

Reviewer feedback:
{reviewer_feedback if reviewer_feedback else "No reviewer feedback provided."}

Return the complete improved Python source code only.
"""
