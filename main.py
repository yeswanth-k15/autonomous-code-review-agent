
from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Autonomous Code Review Agent",
    description=(
        "AI-powered code review and refactoring "
        "using LangGraph and human approval."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Autonomous Code Review Agent API",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "code-review-agent",
    }
