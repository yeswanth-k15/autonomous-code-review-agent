# Autonomous Code Review Agent

An AI-powered autonomous code review and refactoring agent built using **LangGraph, Python, and FastAPI**.

The agent analyzes Python code in GitHub Pull Requests, identifies code quality issues, proposes improvements using an LLM, and allows a human reviewer to approve or reject the suggested changes before they are committed.

## Features

- **GitHub Pull Request Integration:** Fetches Python files and commit information from a GitHub Pull Request.
- **Automated Code Analysis:** Uses Flake8 and Black to identify linting and formatting issues.
- **AI-Powered Refactoring:** Uses an LLM to analyze code and generate improved versions.
- **Human-in-the-Loop Approval:** Allows reviewers to inspect proposed changes and provide feedback before changes are applied.
- **Feedback-Based Refinement:** Sends rejected suggestions back through the refactoring process.
- **Safe GitHub Commits:** Validates file paths and checks that the Pull Request has not changed since the review started.
- **Persistent Workflow State:** Uses LangGraph checkpointing to preserve review progress.
- **REST API:** Provides FastAPI endpoints for GitHub webhook handling and reviewer approval.

## Architecture

The application uses LangGraph to orchestrate the code review workflow.

### Workflow

1. **Fetch PR:** Retrieves Python source files and the Pull Request's head commit SHA.
2. **Lint Code:** Runs automated code quality and formatting checks in an isolated Docker container.
3. **Propose Refactoring:** Uses an LLM to analyze the code and generate improved versions.
4. **Human Review:** Pauses the workflow so a reviewer can approve or reject the proposed changes.
5. **Apply Changes:** If approved, commits the refactored files to the Pull Request branch. If rejected, reviewer feedback is sent back for another refinement cycle.

### Main LangGraph Nodes

| Node | Responsibility |
|---|---|
| `fetch_pr_node` | Fetches Pull Request files and commit SHA |
| `lint_code_node` | Runs code quality checks |
| `propose_refactor_node` | Generates AI-powered refactoring suggestions |
| `apply_changes_node` | Commits approved changes to GitHub |

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3.11 |
| Workflow Orchestration | LangGraph |
| LLM Integration | LangChain, OpenAI |
| Backend Framework | FastAPI |
| Version Control | Git, GitHub API |
| Code Quality | Flake8, Black |
| Execution Isolation | Docker |
| Workflow Persistence | LangGraph Checkpointing, SQLite |
| Testing | Pytest |

## Project Structure

```text
autonomous-code-review-agent/
│
├── app/
│   ├── agent/
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── graph.py
│   │   └── prompts.py
│   │
│   ├── api/
│   │   └── routes.py
│   │
│   ├── services/
│   │   ├── github_service.py
│   │   ├── github_commit_service.py
│   │   ├── webhook_security.py
│   │   └── webhook_delivery_service.py
│   │
│   └── tools/
│       └── linter_tool.py
│
├── docker/
│   └── linter/
│       └── Dockerfile
│
├── tests/
│
├── .env.example
├── .gitignore
├── main.py
├── requirements.txt
├── openapi.json
└── README.md
```

## Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.11
- Git
- Docker Desktop
- GitHub Personal Access Token with the required repository permissions
- OpenAI API Key

### 1. Clone the Repository

```bash
git clone https://github.com/yeswanth-k15/autonomous-code-review-agent.git

cd autonomous-code-review-agent
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

Configure the following variables:

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
WEBHOOK_SECRET=your_github_webhook_secret
REVIEWER_API_TOKEN=your_secure_reviewer_token
APP_ENV=development
CHECKPOINT_DB_PATH=checkpoints.sqlite
```

Replace the placeholder values with your own credentials. Never commit your `.env` file or expose API keys.

### 5. Build the Docker Linter Image

Make sure Docker Desktop is running, then execute:

```bash
docker build -t code-review-linter:latest -f docker/linter/Dockerfile .
```

### 6. Run the Application

```bash
python -m uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Application information |
| `GET` | `/health` | Health check |
| `POST` | `/api/webhooks/github` | Receives GitHub webhook events |
| `POST` | `/api/reviews/{thread_id}/approve` | Submits reviewer approval or rejection |

### OpenAPI Specification

The generated OpenAPI specification is available in `openapi.json`.

FastAPI interactive documentation:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`


### Reviewer Authentication

The review approval endpoint is protected using Bearer Token authentication.

Every approval or rejection request must include the following HTTP header:

```http
Authorization: Bearer YOUR_REVIEWER_API_TOKEN
```

Configure `REVIEWER_API_TOKEN` in your `.env` file before starting the application.

The application rejects requests with missing or invalid tokens. If the reviewer token is not configured on the server, the endpoint returns 503 Service Unavailable.

Important: Never expose your reviewer token or commit your .env file to GitHub.

The webhook endpoint validates GitHub webhook signatures and handles delivery IDs to avoid processing duplicate deliveries.


## Running Tests

Run the complete test suite:

```bash
python -m pytest -v
```

The test suite covers workflow state, GitHub integration, linting, refactoring, API behavior, webhook security, and commit handling.

## Security Considerations

- API credentials are loaded from environment variables.
- GitHub webhook signatures are validated using HMAC.
- Duplicate webhook deliveries are handled using delivery IDs.
- Linting runs inside a restricted Docker container.
- File paths are validated before committing changes.
- Pull Request commit SHA validation helps prevent applying changes to an outdated branch state.
- Human approval is required before the workflow applies changes.

**Deployment note:** Before exposing the application publicly, protect the approval endpoint with appropriate authentication and authorization, and configure HTTPS and secure webhook delivery.

## Future Improvements

- Implement role-based reviewer authorization and stronger production authentication.
- Add support for additional programming languages.
- Improve AI-generated code review explanations.
- Add review reports and code quality metrics.
- Add production deployment and monitoring.
- Expand end-to-end integration testing.

## Author

**Yeswanth Kalivarapu**

GitHub: [yeswanth-k15](https://github.com/yeswanth-k15)

---

*Built as an AI-powered code review and refactoring system using LangGraph, Python, FastAPI, and GitHub integration.*