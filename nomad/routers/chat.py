import json
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from nomad.agent.deep_agent import deep_agent_manager

router = APIRouter(prefix="/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    thread_id: str = Field("default", description="Conversation thread ID")
    active_note_title: Optional[str] = Field(None, description="Title of note active in Obsidian")
    active_note_content: Optional[str] = Field(None, description="Current content of active note")
    active_note_path: Optional[str] = Field(None, description="Path of active note in vault")
    vault_path: Optional[str] = Field(None, description="Vault directory path")
    model: Optional[str] = Field(None, description="Fireworks model override")
    api_key: Optional[str] = Field(None, description="Fireworks API key override")
    stream: bool = Field(True, description="Whether to stream response events")


@router.post("")
async def chat_endpoint(
    req: ChatRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    api_key = req.api_key or x_fireworks_api_key

    # Build prompt, incorporating active note context if provided
    prompt_parts = []
    if req.active_note_title or req.active_note_path:
        note_id = req.active_note_title or req.active_note_path
        prompt_parts.append(f"[Active Note: {note_id}]")
    if req.active_note_content:
        prompt_parts.append(f"[Active Note Content]:\n```markdown\n{req.active_note_content}\n```")
    prompt_parts.append(req.message)
    full_prompt = "\n\n".join(prompt_parts)

    if not req.stream:
        try:
            result = await deep_agent_manager.invoke_agent(
                prompt=full_prompt,
                thread_id=req.thread_id,
                vault_path=req.vault_path,
                model=req.model,
                api_key=api_key,
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat execution failed: {str(e)}")

    # SSE streaming response
    async def event_generator():
        try:
            async for event in deep_agent_manager.stream_agent(
                prompt=full_prompt,
                thread_id=req.thread_id,
                vault_path=req.vault_path,
                model=req.model,
                api_key=api_key,
            ):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            err_payload = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
