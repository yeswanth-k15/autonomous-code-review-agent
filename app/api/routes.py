
import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command
from pydantic import BaseModel

from app.agent.graph import review_graph
from app.agent.state import create_initial_state
from app.services.webhook_delivery_service import (
    claim_webhook_delivery,
    release_webhook_delivery,
)
from app.services.webhook_security import verify_github_signature

load_dotenv()

router = APIRouter()


class ApprovalRequest(BaseModel):
    is_approved: bool
    reviewer_feedback: str = ""


@router.post("/api/webhooks/github")
async def github_webhook(request: Request):
    """Receive and verify GitHub pull request webhook events."""

    signature = request.headers.get("X-Hub-Signature-256")
    payload_body = await request.body()

    # Step 1: Verify the GitHub webhook signature.
    if not verify_github_signature(payload_body, signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing GitHub webhook signature.",
        )

    # Step 2: Validate the delivery ID.
    delivery_id = request.headers.get("X-GitHub-Delivery")

    if not delivery_id or not delivery_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Missing GitHub webhook delivery ID.",
        )

    # Step 3: Parse the JSON payload.
    try:
        payload = json.loads(payload_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        )

    pull_request = payload.get("pull_request")

    if not pull_request:
        raise HTTPException(
            status_code=400,
            detail="Payload does not contain a pull request.",
        )

    pr_url = pull_request.get("html_url")

    if not pr_url:
        raise HTTPException(
            status_code=400,
            detail="Pull request URL is missing.",
        )

    repository_name = payload.get("repository", {}).get("full_name")
    pr_number = pull_request.get("number")

    if not repository_name or pr_number is None:
        raise HTTPException(
            status_code=400,
            detail="Repository name or pull request number is missing.",
        )

    # Step 4: Register the delivery ID.
    try:
        is_new_delivery = claim_webhook_delivery(delivery_id)

        if not is_new_delivery:
            return {
                "message": "Webhook delivery already processed.",
                "delivery_id": delivery_id,
                "status": "duplicate",
            }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to register webhook delivery.",
        )

    # Step 5: Start the review workflow.
    thread_id = f"{repository_name}-{pr_number}"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        initial_state = create_initial_state(pr_url)

        result = await review_graph.ainvoke(
            initial_state,
            config=config,
        )

        return {
            "message": "Code review workflow started.",
            "thread_id": thread_id,
            "delivery_id": delivery_id,
            "status": "waiting_for_review",
            "interrupted": bool(result.get("__interrupt__")),
        }

    except Exception:
        # Release the delivery ID so GitHub can retry after a failure.
        try:
            release_webhook_delivery(delivery_id)
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Failed to start review workflow.",
        )


@router.post("/api/reviews/{thread_id}/approve")
async def approve_review(
    thread_id: str,
    request: ApprovalRequest,
):
    """Submit reviewer feedback and resume the workflow."""

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        snapshot = review_graph.get_state(config)

        if not snapshot.values:
            raise HTTPException(
                status_code=404,
                detail="Review thread not found.",
            )

        if not snapshot.next:
            raise HTTPException(
                status_code=409,
                detail="Review workflow is not waiting for input.",
            )

        result = await review_graph.ainvoke(
            Command(
                resume={
                    "is_approved": request.is_approved,
                    "reviewer_feedback": request.reviewer_feedback,
                }
            ),
            config=config,
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
            detail=f"Failed to submit review: {str(error)}",
        )
