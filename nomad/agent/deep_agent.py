import os
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator
from langchain_fireworks import ChatFireworks
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from nomad.config import settings
from nomad.agent.tools import get_custom_vault_tools

NOMAD_SYSTEM_PROMPT = """You are Nomad, an autonomous knowledge agent integrated with the user's Obsidian vault.

Your Core Capabilities:
1. Note Taking & Knowledge Management: You synthesize, outline, connect, and structure notes.
2. Obsidian Syntax: Use clean Markdown with Obsidian features:
   - Internal links: `[[Note Name]]` or `[[Note Name|Custom Text]]`
   - Tags: `#tag` or `#nested/tag`
   - Callouts: `> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`, `> [!TODO]`, `> [!SUMMARY]`
   - Formatted tables with proper pipe alignment.
3. Vault Exploration & Tool Calling:
   - You have access to the user's vault filesystem (`ls`, `read_file`, `write_file`, `edit_file`, `grep`, `glob`).
   - You have vault-specific tools: `search_vault`, `find_backlinks`, `list_vault_tags`, and `create_vault_note`.
   - When asked to organize or cross-reference, find relevant existing notes and reference them with `[[...]]`.
4. Multi-step Planning:
   - For complex, multi-note tasks or broad research, use `write_todos` to plan your steps before executing.
   - When editing existing notes, be precise and preserve the author's voice and existing links.
"""


class DeepAgentManager:
    def __init__(self):
        self.checkpointer = InMemorySaver()
        self._cached_agents: Dict[str, Any] = {}

    def _get_agent(
        self,
        vault_path: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        key = api_key or settings.fireworks_api_key or os.getenv("FIREWORKS_API_KEY")
        if not key:
            raise ValueError(
                "Fireworks API key is not configured. Please set FIREWORKS_API_KEY in .env, environment, or plugin settings."
            )

        chosen_model = model or settings.fireworks_model
        resolved_vault = Path(vault_path).expanduser().resolve() if vault_path else settings.get_vault_path()

        cache_key = f"{chosen_model}_{str(resolved_vault)}"
        if cache_key in self._cached_agents:
            return self._cached_agents[cache_key]

        llm = ChatFireworks(
            model=chosen_model,
            api_key=key,
            temperature=0.2,
        )

        custom_tools = get_custom_vault_tools()
        backend = FilesystemBackend(root_dir=resolved_vault) if resolved_vault and resolved_vault.is_dir() else None

        agent_kwargs: Dict[str, Any] = {
            "model": llm,
            "tools": custom_tools,
            "system_prompt": NOMAD_SYSTEM_PROMPT,
            "checkpointer": self.checkpointer,
        }
        if backend:
            agent_kwargs["backend"] = backend

        agent = create_deep_agent(**agent_kwargs)
        self._cached_agents[cache_key] = agent
        return agent

    async def invoke_agent(
        self,
        prompt: str,
        thread_id: str = "default",
        vault_path: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        agent = self._get_agent(vault_path=vault_path, model=model, api_key=api_key)
        config = {"configurable": {"thread_id": thread_id}}

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config
        )

        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        response_text = ""
        if last_message:
            content = last_message.content
            if isinstance(content, list):
                response_text = "".join(
                    str(c) if isinstance(c, str) else c.get("text", "") for c in content
                )
            else:
                response_text = str(content)

        return {
            "response": response_text.strip(),
            "thread_id": thread_id,
            "messages_count": len(messages),
        }

    async def stream_agent(
        self,
        prompt: str,
        thread_id: str = "default",
        vault_path: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        agent = self._get_agent(vault_path=vault_path, model=model, api_key=api_key)
        config = {"configurable": {"thread_id": thread_id}}

        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
            version="v2",
        ):
            event_type = event.get("event")
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text_delta = chunk.content
                    if isinstance(text_delta, str):
                        yield {"type": "token", "content": text_delta}
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "tool")
                tool_input = event.get("data", {}).get("input", {})
                yield {"type": "tool_start", "tool": tool_name, "input": tool_input}
            elif event_type == "on_tool_end":
                tool_name = event.get("name", "tool")
                tool_output = str(event.get("data", {}).get("output", ""))
                # Truncate long tool outputs in events for UI display
                display_output = tool_output[:200] + "..." if len(tool_output) > 200 else tool_output
                yield {"type": "tool_end", "tool": tool_name, "output": display_output}


deep_agent_manager = DeepAgentManager()
