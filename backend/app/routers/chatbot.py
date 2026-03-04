"""
Phase 7 Router: POST /api/v1/chatbot — The DevLens Architect endpoint.

Handles three flows:
  1. New Mission     — user provides an issue number → full investigation pipeline
  2. Terminal Output — user pastes a terminal error during an active mission
  3. Follow-up Chat  — general Q&A within mission context
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.architect_agent import (
    run_full_investigation,
    handle_terminal_output,
    handle_followup,
    get_session,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chatbot"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    owner: str
    repo: str
    message: str
    mission_id: str | None = None          # e.g. "issue-42"
    current_step: int | None = None
    type: str = "user_chat"                # "user_chat" | "terminal_output"
    issue_number: int | None = None        # triggers full investigation
    user_profile: dict | None = None       # {level, language, goal} for persona-aware tone


class ChatResponse(BaseModel):
    reply: str
    mission_id: str | None = None
    mode: str | None = None                # "exterminator" | "builder" | "janitor"
    plan: str | None = None
    relevant_files: list[str] | None = None
    blast_radius: list[str] | None = None
    git_commands: str | None = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/chatbot",
    response_model=ChatResponse,
    summary="DevLens Architect — Agentic Contribution Engine",
)
async def chatbot(request: ChatRequest) -> ChatResponse:
    """
    Main chatbot endpoint. Routes to three flows:

    1. **New Mission** (`issue_number` is set):
       Runs the full pipeline — Investigate → Snipe → Plan → Command.

    2. **Terminal Output** (`type == "terminal_output"` + `mission_id`):
       Analyses error output against the active mission plan.

    3. **Follow-up Chat** (default):
       Answers questions using mission context.
    """

    # ── Flow 1: New Mission (full investigation) ──
    if request.issue_number is not None:
        try:
            result = await run_full_investigation(
                owner=request.owner,
                repo=request.repo,
                issue_text=request.message,
                issue_number=request.issue_number,
                user_profile=request.user_profile,
            )
            return ChatResponse(
                reply=result["reply"],
                mission_id=result["mission_id"],
                mode=result["mode"],
                plan=result["plan"],
                relevant_files=result["relevant_files"],
                blast_radius=result["blast_radius"],
                git_commands=result["git_commands"],
            )
        except Exception as exc:
            logger.exception("Full investigation failed")
            raise HTTPException(status_code=500, detail=str(exc))

    # ── Flow 2: Terminal Output Analysis ──
    if request.type == "terminal_output" and request.mission_id:
        session = get_session(request.mission_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"No active mission found for '{request.mission_id}'. Start a new mission by providing an issue_number.",
            )

        # Update current step if provided
        if request.current_step is not None:
            session["current_step"] = request.current_step

        try:
            analysis = await handle_terminal_output(
                terminal_output=request.message,
                mission_context=session,
                user_profile=request.user_profile,
            )
            return ChatResponse(
                reply=analysis,
                mission_id=request.mission_id,
                mode=session.get("mode"),
            )
        except Exception as exc:
            logger.exception("Terminal output analysis failed")
            raise HTTPException(status_code=500, detail=str(exc))

    # ── Flow 3: Follow-up Chat ──
    mission_context: dict = {}
    if request.mission_id:
        session = get_session(request.mission_id)
        if session:
            mission_context = session

    if not mission_context:
        # No active mission — treat as a simple question
        from app.services.bedrock_client import call_claude
        from app.services.persona import UserProfile, build_persona_modifier
        persona_suffix = ""
        if request.user_profile:
            try:
                persona_suffix = "\n\n" + build_persona_modifier(UserProfile(**request.user_profile))
            except Exception:
                pass
        try:
            reply = await call_claude(
                "You are DevLens Architect, a helpful AI pair programmer for open-source contributions. "
                "Answer the user's question concisely. Use markdown formatting." + persona_suffix,
                request.message,
                max_tokens=1000,
            )
            return ChatResponse(reply=reply)
        except Exception as exc:
            logger.exception("Simple chat failed")
            raise HTTPException(status_code=500, detail=str(exc))

    try:
        reply = await handle_followup(
            message=request.message,
            mission_context=mission_context,
            user_profile=request.user_profile,
        )
        return ChatResponse(
            reply=reply,
            mission_id=request.mission_id,
            mode=mission_context.get("mode"),
        )
    except Exception as exc:
        logger.exception("Follow-up chat failed")
        raise HTTPException(status_code=500, detail=str(exc))
