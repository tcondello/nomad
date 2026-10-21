# Nomad Agent for Obsidian 🧭

**Nomad Agent** is an agentic AI writing, formatting, and research companion for Obsidian powered by **LangChain DeepAgents** and **Fireworks AI**.

## Highlights

- **Inline Writing & Formatting**: Standardize Markdown headers, fix formatting, polish tone, summarize, and expand bullet points into paragraphs directly in the editor.
- **Deep Agent Research & Knowledge Integration**: Runs multi-step tasks across your Obsidian vault with built-in tools (`search_vault`, `find_backlinks`, `list_vault_tags`, `create_vault_note`, `read_file`, `write_file`, `edit_file`) and planning (`write_todos`).
- **Sidebar Chat Assistant**: Real-time streaming conversation in Obsidian's right sidebar with one-click active note context attachment and "Insert to Note" actions.

## Quick Installation

1. Copy `manifest.json`, `main.js`, and `styles.css` to `<YourVault>/.obsidian/plugins/nomad-agent/`.
2. In Obsidian, go to **Settings** > **Community plugins** and turn off Restricted mode.
3. Enable **Nomad Agent** in the installed plugins list.
4. Ensure your Nomad backend server is running (`nomad start`) and configured with your Fireworks AI key.

## License

MIT License. See [LICENSE](../LICENSE) for details.
