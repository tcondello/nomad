# Nomad: Obsidian Agentic Harness 🧭

**Nomad** is an agentic AI harness integrating **Obsidian** with **LangChain DeepAgents** and **Fireworks AI**. It turns Obsidian into an agent-assisted knowledge workstation, providing:

1. **Inline Writing & Formatting Actions** directly in the Obsidian editor (hotkeys, context menu, slash/palette commands).
2. **Deep Agent Tool Execution** using LangChain's `deepagents` framework with direct filesystem and vault-level tools (`search_vault`, `find_backlinks`, `list_vault_tags`, `create_vault_note`, `read_file`, `write_file`, `edit_file`, and planning via `write_todos`).
3. **Interactive Sidebar Chat View** inside Obsidian with real-time streaming, active note context awareness, and one-click markdown insertion.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   Obsidian Client                      │
│  ┌───────────────────────┐  ┌────────────────────────┐ │
│  │ Inline Editor Actions │  │   Nomad Sidebar Chat   │ │
│  │ (Format, Polish,      │  │ (Streaming, Note       │ │
│  │  Expand, Summarize,   │  │  Context, Tool Logs)   │ │
│  │  Custom Modal)        │  │                        │ │
│  └───────────┬───────────┘  └───────────┬────────────┘ │
└──────────────┼──────────────────────────┼──────────────┘
               │ HTTP / SSE               │
               ▼                          ▼
┌────────────────────────────────────────────────────────┐
│               Nomad Backend (FastAPI)                  │
│                                                        │
│  ┌─────────────────────────┐ ┌──────────────────────┐  │
│  │  Inline Writing Engine  │ │  DeepAgent Manager   │  │
│  │  - Low-latency prompts  │ │  - LangChain DeepAgent│ │
│  │  - Markdown cleaning    │ │  - FilesystemBackend │  │
│  │  - Tone & grammar       │ │  - Planning & Todos  │  │
│  └───────────┬─────────────┘ └──────────┬───────────┘  │
│              │                          │              │
│              ▼                          ▼              │
│       ┌──────────────┐           ┌──────────────┐      │
│       │ Fireworks AI │           │Obsidian Vault│      │
│       │ LLM API      │           │(Local Disk)  │      │
│       └──────────────┘           └──────────────┘      │
└────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Configure Environment

Copy `.env.example` to `.env` and provide your Fireworks AI API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
FIREWORKS_API_KEY=your_fireworks_api_key_here
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### 2. Start the Nomad Server

Using `uv`:
```bash
uv run nomad start
```

Or via the virtual environment:
```bash
source .venv/bin/activate
nomad start
```

The server will start at `http://127.0.0.1:8765`.

### 3. Install the Obsidian Plugin

Run the automated installer:
```bash
uv run nomad install-plugin /path/to/your/obsidian/vault
```

Then in Obsidian:
1. Open **Settings** -> **Community plugins**.
2. Make sure Restricted Mode is turned **OFF**.
3. In **Installed plugins**, enable **Nomad Agent**.
4. Click the gear icon next to Nomad Agent to verify the server connection.

---

## Features

### ⚡ Inline Editor Actions
Select any text in Obsidian (or run on the whole note):
- **Format & Clean Note**: Aligns Markdown tables, normalizes heading hierarchies, fixes list indentation, validates YAML frontmatter, and preserves `[[wikilinks]]`.
- **Polish Tone & Grammar**: Fixes spelling, punctuation, and awkward phrasing while matching your desired tone (Concise, Professional, Academic, Casual, Technical).
- **Expand Bullets / Thoughts**: Takes bullet points or rough outlines and fleshes them out into well-structured paragraphs with examples.
- **Summarize Selection / Note**: Produces an executive summary and key takeaways.
- **Ask Nomad (Inline Modal)** (`Cmd+Shift+I` or via command palette): Enter any custom prompt (e.g. *"Convert this table into a feature comparison matrix"*, *"Extract action items with checkboxes"*) and choose whether to replace selection or insert below.

### 🧠 LangChain Deep Agent & Tool Calling
Powered by `deepagents.create_deep_agent` with:
- **Filesystem Backend**: Directly reads and edits notes in the vault safely.
- **Vault Tools**:
  - `search_vault`: Search across all `.md` files for keywords or topics.
  - `find_backlinks`: Find which notes link to a given note.
  - `list_vault_tags`: Aggregates all `#tags` across your knowledge base.
  - `create_vault_note`: Generates new notes with proper formatting.
- **Planning & Todos**: Breaks down complex tasks step-by-step using `write_todos`.

### 💬 Sidebar Chat View
Click the Compass icon in the left ribbon or run **Nomad: Open AI Sidebar Chat** to open the chat panel in the right sidebar:
- Chat with your vault.
- Toggle **Include Active Note Context** to send the current note's content along with your message.
- View real-time tool calls and tokens streamed from Fireworks AI.
- One-click copy or insert generated responses directly into your active note.
