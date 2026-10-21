import os
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_fireworks import ChatFireworks
from langchain_core.messages import SystemMessage, HumanMessage
from nomad.config import settings


class InlineAction(str, Enum):
    FORMAT = "format"
    POLISH = "polish"
    EXPAND = "expand"
    SUMMARIZE = "summarize"
    CUSTOM = "custom"


class InlineRequest(BaseModel):
    action: InlineAction
    text: str = Field(..., description="The selected text or note content to transform")
    context_note_path: Optional[str] = Field(None, description="Path of active note for context")
    context_before: Optional[str] = Field(None, description="Surrounding text before selection")
    context_after: Optional[str] = Field(None, description="Surrounding text after selection")
    instruction: Optional[str] = Field(None, description="Custom instruction when action is 'custom'")
    tone: Optional[str] = Field("Professional", description="Tone preference: Concise, Professional, Academic, Casual, Technical")
    model: Optional[str] = Field(None, description="Override Fireworks model")
    api_key: Optional[str] = Field(None, description="Override Fireworks API key")


class InlineResponse(BaseModel):
    result: str
    action: InlineAction
    model_used: str


SYSTEM_PROMPTS: Dict[InlineAction, str] = {
    InlineAction.FORMAT: """You are an expert Markdown editor inside Obsidian.
Your task is to reformat and clean the provided text.
Strict Rules:
1. Ensure valid, clean CommonMark/Obsidian Markdown.
2. Fix heading hierarchy, list indentation, spacing, and ensure Markdown tables are cleanly aligned with pipes.
3. Preserve existing Obsidian links like [[Note Name]] or [[Note Name|Alias]] and tags like #tag without modifying them.
4. If there is YAML frontmatter (`---`), ensure it is valid YAML.
5. DO NOT add conversational filler (e.g., 'Here is the formatted text:').
6. Output ONLY the resulting formatted markdown text directly.
""",

    InlineAction.POLISH: """You are a master writing coach and copyeditor.
Your task is to fix grammar, spelling, punctuation, and refine phrasing to enhance clarity and flow.
Strict Rules:
1. Maintain the author's original intent, facts, and key terminology.
2. Match the requested tone (e.g., Concise, Professional, Academic, Casual).
3. Preserve all Obsidian links ([[...]]) and tags (#...).
4. DO NOT add conversational filler (e.g., 'Here is the edited version:').
5. Output ONLY the resulting text directly.
""",

    InlineAction.EXPAND: """You are a collaborative writing partner inside Obsidian.
Your task is to expand the provided notes, bullets, or unfinished thoughts into well-articulated, cohesive Markdown prose.
Strict Rules:
1. Flesh out the ideas logically, adding relevant context, examples, or transitional explanations.
2. Structure with clean Markdown (subheadings, paragraphs, or callouts like `> [!NOTE]`).
3. Preserve all existing links ([[...]]) and tags.
4. DO NOT add meta-comments or conversational filler.
5. Output ONLY the expanded content.
""",

    InlineAction.SUMMARIZE: """You are an analytical researcher and note summarizer inside Obsidian.
Your task is to distill the provided content into a high-impact summary.
Strict Rules:
1. Provide a concise TL;DR followed by key bullet points or takeaways.
2. Highlight actionable items, decisions, or core concepts.
3. Use clean Obsidian Markdown.
4. DO NOT include meta-talk like 'Here is a summary:'.
5. Output ONLY the summary content.
""",

    InlineAction.CUSTOM: """You are an AI assistant and markdown editor inside Obsidian.
Your task is to transform or generate content based strictly on the user's specific instruction.
Strict Rules:
1. Follow the user's instruction precisely on the provided text.
2. Output clean Obsidian Markdown.
3. Preserve Obsidian links ([[...]]) unless asked to modify them.
4. DO NOT include conversational preamble or pleasantries. Output ONLY the direct result.
"""
}


class InlineEngine:
    def __init__(self):
        pass

    def _get_llm(self, model: Optional[str] = None, api_key: Optional[str] = None, temperature: float = 0.2) -> ChatFireworks:
        key = api_key or settings.fireworks_api_key or os.getenv("FIREWORKS_API_KEY")
        if not key:
            raise ValueError(
                "Fireworks API key is not configured. Set FIREWORKS_API_KEY in your environment, .env file, or plugin settings."
            )
        chosen_model = model or settings.fireworks_model
        return ChatFireworks(
            model=chosen_model,
            api_key=key,
            temperature=temperature,
        )

    async def execute(self, req: InlineRequest) -> InlineResponse:
        system_base = SYSTEM_PROMPTS.get(req.action, SYSTEM_PROMPTS[InlineAction.CUSTOM])
        if req.tone:
            system_base += f"\nTarget Tone: {req.tone}."

        user_content_parts = []
        if req.context_note_path:
            user_content_parts.append(f"Note Context: {req.context_note_path}")

        if req.action == InlineAction.CUSTOM and req.instruction:
            user_content_parts.append(f"Instruction: {req.instruction}")

        if req.context_before:
            user_content_parts.append(f"--- Surrounding context before ---\n{req.context_before}\n--- End context before ---")

        user_content_parts.append(f"--- Target Text to Process ---\n{req.text}\n--- End Target Text ---")

        if req.context_after:
            user_content_parts.append(f"--- Surrounding context after ---\n{req.context_after}\n--- End context after ---")

        user_content = "\n\n".join(user_content_parts)

        temp = 0.1 if req.action in (InlineAction.FORMAT, InlineAction.POLISH) else 0.5
        llm = self._get_llm(model=req.model, api_key=req.api_key, temperature=temp)

        messages = [
            SystemMessage(content=system_base),
            HumanMessage(content=user_content),
        ]

        response = await llm.ainvoke(messages)
        result_text = response.content
        if isinstance(result_text, list):
            result_text = "".join(
                str(part) if isinstance(part, str) else part.get("text", "")
                for part in result_text
            )

        model_name = req.model or settings.fireworks_model
        return InlineResponse(
            result=result_text.strip(),
            action=req.action,
            model_used=model_name
        )


inline_engine = InlineEngine()
