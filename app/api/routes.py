
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langgraph.types import Command

from app.agent.graph import review_graph
from app.agent.state import create_initial_state

router = APIRouter()


class ApprovalRequest(BaseModel):
    is_approved: bool
    reviewer_feedback: str = ""


@router.post("/api/webhooks/github")
async def github_webhook(payload: dict):
    """
    Receive GitHub pull request webhook events
    and start the code review workflow.
    """

    pull_request = payload.get("pull_request")

    if not pull_request:
        raise HTTPException(
            status_code=400,
            detail="Payload does not contain a pull request."
        )

    pr_url = pull_request.get("html_url")

    if not pr_url:
        raise HTTPException(
            status_code=400,
            detail="Pull request URL is missing."
        )

    thread_id = str(
        payload.get("repository", {}).get("full_name", "")
    ) + "-" + str(pull_request.get("number", ""))

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:
        initial_state = create_initial_state(pr_url)

        result = await review_graph.ainvoke(
            initial_state,
            config=config
        )

        return {
            "message": "Code review workflow started.",
            "thread_id": thread_id,
            "status": "waiting_for_review",
            "interrupted": bool(result.get("__interrupt__")),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start review: {str(error)}"
        )


@router.post("/api/reviews/{thread_id}/approve")
async def approve_review(
    thread_id: str,
    request: ApprovalRequest
):
    """
    Submit reviewer feedback and resume the workflow.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:
        snapshot = review_graph.get_state(config)

        if not snapshot.values:
            raise HTTPException(
                status_code=404,
                detail="Review thread not found."
            )

        if not snapshot.next:
            raise HTTPException(
                status_code=409,
                detail="Review workflow is not waiting for input."
            )

        result = await review_graph.ainvoke(
            Command(
                resume={
                    "is_approved": request.is_approved,
                    "reviewer_feedback": request.reviewer_feedback,
                }
            ),
            config=config
        )

        return {
            "message": "Review decision submitted.",
            "thread_id": thread_id,
            "is_approved": request.is_approved,
            "interrupted": bool(result.get("__interrupt__")),
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit review: {str(error)}"
        )
