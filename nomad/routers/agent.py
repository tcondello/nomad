from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from nomad.agent.deep_agent import deep_agent_manager

router = APIRouter(prefix="/v1/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    prompt: str = Field(..., description="The user instructions or goal for the deep agent")
    thread_id: str = Field("default", description="Conversation thread id for persistence")
    vault_path: Optional[str] = Field(None, description="Obsidian vault path to operate within")
    model: Optional[str] = Field(None, description="Fireworks model override")
    api_key: Optional[str] = Field(None, description="Fireworks API key override")


class AgentRunResponse(BaseModel):
    response: str
    thread_id: str
    messages_count: int


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    req: AgentRunRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    try:
        api_key = req.api_key or x_fireworks_api_key
        result = await deep_agent_manager.invoke_agent(
            prompt=req.prompt,
            thread_id=req.thread_id,
            vault_path=req.vault_path,
            model=req.model,
            api_key=api_key,
        )
        return AgentRunResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepAgent execution failed: {str(e)}")
