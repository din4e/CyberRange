from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cyberrange.core.manager import RangeManager

app = typer.Typer(
    name="cyberrange",
    help="CyberRange management CLI - manage Docker-based cyber range environments.",
    no_args_is_help=True,
)

console = Console()
manager = RangeManager()


@app.command()
def start(
    range_ref: str = typer.Argument(
        ..., help="Range reference: <category>/<name> (e.g., pentest/cfs)"
    ),
    instance: int = typer.Option(
        1, "--instance", "-i", help="Instance number for multi-instance support"
    ),
):
    """Start a range instance."""
    try:
        info = manager.start_range(range_ref, instance_id=instance)
    except (FileNotFoundError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(
        f"[green]Started[/green] {range_ref} instance {instance} "
        f"(project: {info.project_name})"
    )

    runtimes = manager.get_status(range_ref, instance)
    if runtimes:
        rt = runtimes[0]
        if rt.access_urls:
            console.print()
            for svc, url in rt.access_urls.items():
                console.print(f"  [cyan]{svc}:[/cyan] {url}")


@app.command()
def stop(
    range_ref: str = typer.Argument(
        ..., help="Range reference: <category>/<name>"
    ),
    instance: int = typer.Option(
        1, "--instance", "-i", help="Instance number to stop"
    ),
    remove: bool = typer.Option(
        False, "--remove", "-r", help="Remove containers and networks (down)"
    ),
    volumes: bool = typer.Option(
        False, "--volumes", "-v", help="Also remove volumes (implies --remove)"
    ),
):
    """Stop a running range instance."""
    try:
        manager.stop_range(range_ref, instance_id=instance, remove=remove or volumes, volumes=volumes)
    except (FileNotFoundError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[green]Stopped[/green] {range_ref} instance {instance}")


@app.command()
def status(
    range_ref: Optional[str] = typer.Argument(
        None, help="Range reference (omit for all)"
    ),
    instance: Optional[int] = typer.Option(
        None, "--instance", "-i", help="Specific instance number"
    ),
):
    """Show status of range instances."""
    runtimes = manager.get_status(range_ref, instance)
    if not runtimes:
        console.print("[yellow]No instances found.[/yellow]")
        return

    table = Table(title="CyberRange Instances")
    table.add_column("Range", style="cyan")
    table.add_column("Instance", justify="right")
    table.add_column("Project", style="green")
    table.add_column("Status")
    table.add_column("Services")
    table.add_column("Access URLs")

    for rt in runtimes:
        svc_list = ", ".join(s.name for s in rt.services) if rt.services else "-"
        urls = "\n".join(f"{k}: {v}" for k, v in rt.access_urls.items()) or "-"
        status_style = "green" if rt.status.value == "running" else "yellow"
        table.add_row(
            rt.range_key,
            str(rt.instance_id),
            rt.project_name,
            f"[{status_style}]{rt.status.value}[/{status_style}]",
            svc_list,
            urls,
        )

    console.print(table)


@app.command(name="list")
def list_cmd():
    """List all discovered ranges."""
    ranges = manager.list_ranges()
    if not ranges:
        console.print("[yellow]No ranges discovered.[/yellow]")
        return

    table = Table(title="Discovered Ranges")
    table.add_column("Range Key", style="cyan")
    table.add_column("Category")
    table.add_column("Name")
    table.add_column("Services", justify="right")
    table.add_column("Networks", justify="right")
    table.add_column("Instances")

    for r in ranges:
        instances = r.get("running_instances", [])
        inst_str = ", ".join(
            f"#{i['instance_id']}" for i in instances
        ) if instances else "-"
        table.add_row(
            r["range_key"],
            r["category"],
            r["name"],
            str(r["total_services"]),
            str(len(r.get("networks", []))),
            inst_str,
        )

    console.print(table)


@app.command()
def stats(
    range_ref: Optional[str] = typer.Argument(
        None, help="Range reference (omit for all)"
    ),
    instance: Optional[int] = typer.Option(
        None, "--instance", "-i", help="Specific instance number"
    ),
):
    """Show usage statistics."""
    project_name = None
    if range_ref:
        name = range_ref.split("/")[-1]
        project_name = f"{name}-{instance or 1}"

    data = manager.stats_tracker.get_stats(project_name)
    if not data:
        console.print("[yellow]No statistics available.[/yellow]")
        return

    if project_name:
        _print_instance_stats(project_name, data)
    else:
        for pname, s in data.items():
            _print_instance_stats(pname, s)
            console.print()


def _print_instance_stats(project_name: str, s: dict):
    console.print(f"[cyan]{project_name}[/cyan] ({s.get('range_key', '')})")
    console.print(f"  Starts: {s.get('total_starts', 0)}")
    console.print(f"  Stops: {s.get('total_stops', 0)}")
    total = s.get("total_runtime_seconds", 0)
    hours, remainder = divmod(int(total), 3600)
    minutes, seconds = divmod(remainder, 60)
    console.print(f"  Total runtime: {hours}h {minutes}m {seconds}s")
    current = s.get("current_session_seconds")
    if current:
        h, r = divmod(int(current), 3600)
        m, sec = divmod(r, 60)
        console.print(f"  Current session: {h}h {m}m {sec}s")
    console.print(f"  Interactions: {s.get('interaction_count', 0)}")


@app.command()
def serve(
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="MCP transport: stdio or streamable-http"
    ),
    host: str = typer.Option("localhost", "--host"),
    port: int = typer.Option(8000, "--port"),
):
    """Start the MCP server for AI agent integration."""
    from cyberrange.mcp_server import mcp

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host=host, port=port)
