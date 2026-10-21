from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from nomad.agent.inline_engine import (
    InlineRequest,
    InlineResponse,
    InlineAction,
    inline_engine,
)

router = APIRouter(prefix="/v1/inline", tags=["inline"])


@router.post("/transform", response_model=InlineResponse)
async def transform_text(
    req: InlineRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    try:
        if not req.api_key and x_fireworks_api_key:
            req.api_key = x_fireworks_api_key
        return await inline_engine.execute(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inline transform failed: {str(e)}")


@router.post("/format", response_model=InlineResponse)
async def format_note(
    req: InlineRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    req.action = InlineAction.FORMAT
    return await transform_text(req, x_fireworks_api_key)


@router.post("/polish", response_model=InlineResponse)
async def polish_note(
    req: InlineRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    req.action = InlineAction.POLISH
    return await transform_text(req, x_fireworks_api_key)


@router.post("/expand", response_model=InlineResponse)
async def expand_note(
    req: InlineRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    req.action = InlineAction.EXPAND
    return await transform_text(req, x_fireworks_api_key)


@router.post("/summarize", response_model=InlineResponse)
async def summarize_note(
    req: InlineRequest,
    x_fireworks_api_key: Optional[str] = Header(None, alias="X-Fireworks-Api-Key"),
):
    req.action = InlineAction.SUMMARIZE
    return await transform_text(req, x_fireworks_api_key)
