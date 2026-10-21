import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from nomad.config import settings


def _resolve_vault_path(custom_vault: Optional[str] = None) -> Optional[Path]:
    if custom_vault:
        p = Path(custom_vault).expanduser().resolve()
        if p.is_dir():
            return p
    return settings.get_vault_path()


@tool
def search_vault(query: str) -> str:
    """Search Obsidian markdown files in the vault for query keywords or phrases.
    Use this to find relevant notes, context, or previous thoughts.
    """
    vault_path = _resolve_vault_path()
    if not vault_path:
        return "Obsidian vault path is not configured or does not exist."

    matches = []
    regex = re.compile(re.escape(query), re.IGNORECASE)

    for md_file in vault_path.rglob("*.md"):
        # Skip hidden folders like .obsidian or .trash
        if any(part.startswith(".") for part in md_file.relative_to(vault_path).parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if regex.search(content) or regex.search(md_file.stem):
                # Extract excerpt
                lines = content.splitlines()
                matching_lines = [
                    f"Line {idx+1}: {line.strip()}"
                    for idx, line in enumerate(lines)
                    if regex.search(line)
                ][:3]
                rel_path = md_file.relative_to(vault_path)
                excerpt = "\n  ".join(matching_lines) if matching_lines else "Matched in note title."
                matches.append(f"- **[[{rel_path.as_posix()}]]**:\n  {excerpt}")
                if len(matches) >= 8:
                    break
        except Exception:
            continue

    if not matches:
        return f"No notes found matching '{query}' in the vault."
    return "Found matching notes in vault:\n" + "\n\n".join(matches)


@tool
def find_backlinks(note_title: str) -> str:
    """Find all notes in the Obsidian vault that link to the specified note title using [[note_title]]."""
    vault_path = _resolve_vault_path()
    if not vault_path:
        return "Obsidian vault path is not configured."

    clean_title = note_title.replace("[[", "").replace("]]", "").strip()
    pattern = re.compile(rf"\[\[{re.escape(clean_title)}(\|.*?)?\]\]", re.IGNORECASE)
    referencing_notes = []

    for md_file in vault_path.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.relative_to(vault_path).parts):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(content):
                referencing_notes.append(md_file.relative_to(vault_path).as_posix())
        except Exception:
            continue

    if not referencing_notes:
        return f"No backlinks found for '[[{clean_title}]]'."
    links = [f"- [[{p}]]" for p in referencing_notes]
    return f"Notes linking to '[[{clean_title}]]':\n" + "\n".join(links)


@tool
def list_vault_tags() -> str:
    """List tags and topics currently used across markdown notes in the Obsidian vault."""
    vault_path = _resolve_vault_path()
    if not vault_path:
        return "Obsidian vault path is not configured."

    # Obsidian tags: start with # followed by letters/numbers/hyphens/underscores/forward slashes, ending at word boundary or punctuation
    tag_pattern = re.compile(r"(?<!\S)#([a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\-]+)*)")
    tags = set()

    for md_file in vault_path.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.relative_to(vault_path).parts):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Exclude code blocks when collecting tags
            content_no_code = re.sub(r"```[\s\S]*?```", "", content)
            found = tag_pattern.findall(content_no_code)
            for t in found:
                # Exclude purely numeric markdown headers like #1
                if not t.isdigit():
                    tags.add(f"#{t}")
        except Exception:
            continue

    if not tags:
        return "No tags found in the vault."
    sorted_tags = sorted(list(tags))[:50]
    return f"Vault tags ({len(sorted_tags)} found):\n" + ", ".join(sorted_tags)


@tool
def create_vault_note(title: str, content: str, folder: str = "") -> str:
    """Create a new Markdown note inside the Obsidian vault with given title and content.
    Optionally specify a subfolder (e.g. 'Daily', 'Projects', 'Resources').
    """
    vault_path = _resolve_vault_path()
    if not vault_path:
        return "Obsidian vault path is not configured."

    target_dir = vault_path / folder if folder else vault_path
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = title if title.endswith(".md") else f"{title}.md"
    file_path = target_dir / filename

    if file_path.exists():
        return f"Note '{file_path.relative_to(vault_path)}' already exists. Use edit_file to update it."

    file_path.write_text(content, encoding="utf-8")
    return f"Created note [[{file_path.relative_to(vault_path).as_posix()}]] successfully."


def get_custom_vault_tools() -> List[Any]:
    return [search_vault, find_backlinks, list_vault_tags, create_vault_note]
