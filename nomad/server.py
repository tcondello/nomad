import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nomad.config import settings
from nomad.routers import inline, agent, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup banner
    key_status = "Configured" if (settings.fireworks_api_key or os.getenv("FIREWORKS_API_KEY")) else "Missing"
    vault_status = str(settings.get_vault_path()) if settings.get_vault_path() else "Not set"
    print(f"🚀 Nomad Agent Harness starting on {settings.nomad_host}:{settings.nomad_port}")
    print(f"🔑 Fireworks API Key: {key_status}")
    print(f"🧠 Default Model: {settings.fireworks_model}")
    print(f"📁 Obsidian Vault Path: {vault_status}")
    yield
    print("🛑 Nomad Agent Harness shutting down.")


app = FastAPI(
    title="Nomad: Obsidian Agentic Harness",
    description="Agentic harness integrating Obsidian with LangChain DeepAgents and Fireworks AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow CORS for Obsidian client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inline.router)
app.include_router(agent.router)
app.include_router(chat.router)


@app.get("/v1/health")
async def health_check():
    vault_p = settings.get_vault_path()
    has_key = bool(settings.fireworks_api_key or os.getenv("FIREWORKS_API_KEY"))
    return {
        "status": "ok",
        "fireworks_configured": has_key,
        "default_model": settings.fireworks_model,
        "vault_configured": vault_p is not None,
        "vault_path": str(vault_p) if vault_p else None,
    }


@app.get("/v1/models")
async def list_models():
    return {
        "models": [
            {
                "id": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "name": "Llama 3.3 70B Instruct (Default, Fast & Smart)",
                "recommended": True,
            },
            {
                "id": "accounts/fireworks/models/deepseek-r1",
                "name": "DeepSeek R1 (Deep Reasoning & Thought)",
                "recommended": False,
            },
            {
                "id": "accounts/fireworks/models/qwen2p5-72b-instruct",
                "name": "Qwen 2.5 72B Instruct (High Precision)",
                "recommended": False,
            },
            {
                "id": "accounts/fireworks/models/llama-v3p1-8b-instruct",
                "name": "Llama 3.1 8B Instruct (Ultra Fast & Lightweight)",
                "recommended": False,
            },
        ]
    }
