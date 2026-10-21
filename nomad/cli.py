import os
import sys
import shutil
import subprocess
from pathlib import Path
import click
import uvicorn
from nomad.config import settings


@click.group()
def main():
    """Nomad: Agentic harness for Obsidian using LangChain DeepAgents and Fireworks AI."""
    pass


@main.command()
@click.option("--host", default=None, help="Host to bind server to")
@click.option("--port", default=None, type=int, help="Port to bind server to")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code change")
def start(host, port, reload):
    """Start the Nomad Agent server."""
    h = host or settings.nomad_host
    p = port or settings.nomad_port
    click.echo(f"Starting Nomad Agent on http://{h}:{p} ...")
    uvicorn.run("nomad.server:app", host=h, port=p, reload=reload, log_level=settings.log_level.lower())


@main.command()
def status():
    """Check configuration and status of Fireworks and Vault."""
    key = settings.fireworks_api_key or os.getenv("FIREWORKS_API_KEY")
    key_display = f"Set (starts with {key[:6]}...)" if key else "NOT SET"
    vault = settings.get_vault_path()

    click.echo("=== Nomad Agent Status ===")
    click.echo(f"Fireworks API Key: {key_display}")
    click.echo(f"Fireworks Model  : {settings.fireworks_model}")
    click.echo(f"Obsidian Vault   : {vault if vault else 'NOT CONFIGURED'}")
    click.echo(f"Server Target    : http://{settings.nomad_host}:{settings.nomad_port}")
    if not key:
        click.echo("\n[!] To set your API key, copy .env.example to .env and set FIREWORKS_API_KEY.")


@main.command()
@click.argument("vault_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def install_plugin(vault_path):
    """Build and install the Nomad Obsidian plugin into an Obsidian vault."""
    vault = Path(vault_path).expanduser().resolve()
    plugins_dir = vault / ".obsidian" / "plugins" / "nomad-agent"

    repo_root = Path(__file__).parent.parent
    plugin_src = repo_root / "obsidian-plugin"

    if not plugin_src.exists():
        click.echo(f"Error: Plugin source not found at {plugin_src}", err=True)
        sys.exit(1)

    click.echo(f"Building Obsidian plugin in {plugin_src} ...")
    # Run npm run build or pnpm run build
    build_cmd = "pnpm run build" if shutil.which("pnpm") else "npm run build"
    result = subprocess.run(build_cmd, shell=True, cwd=str(plugin_src))
    if result.returncode != 0:
        click.echo("Failed to build plugin.", err=True)
        sys.exit(result.returncode)

    click.echo(f"Installing plugin to {plugins_dir} ...")
    plugins_dir.mkdir(parents=True, exist_ok=True)

    for fname in ["manifest.json", "main.js", "styles.css"]:
        src_file = plugin_src / fname
        if src_file.exists():
            shutil.copy2(src_file, plugins_dir / fname)
            click.echo(f" - Copied {fname}")
        else:
            click.echo(f"Warning: {fname} not found in {plugin_src}", err=True)

    click.echo("\nPlugin successfully installed!")
    click.echo("To activate in Obsidian:")
    click.echo("1. Open Obsidian -> Settings -> Community plugins")
    click.echo("2. Enable community plugins if disabled")
    click.echo("3. Find 'Nomad Agent' in Installed plugins and toggle it ON.")


if __name__ == "__main__":
    main()
