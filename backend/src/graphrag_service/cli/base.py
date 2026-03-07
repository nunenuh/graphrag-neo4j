"""
Base CLI utilities and shared functionality.
"""

from rich.console import Console

console = Console()


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]v[/bold green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]x[/bold red] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]i[/bold blue] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]![/bold yellow] {message}")
