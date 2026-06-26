"""
Test the interactive menu by calling it directly
"""

import sys
import os

# Add prism to path
sys.path.insert(0, '/Users/rahaulmaity/Documents/CrustData')

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Display the menu as it would appear
console.clear()

banner = Panel(
    "[bold cyan]Prism[/bold cyan] - Tech Stack Reverse Engineering Tool\n"
    "Analyze company tech stacks from hiring patterns",
    box=box.DOUBLE,
    border_style="cyan"
)
console.print(banner)
console.print()

# Display menu
menu_table = Table(show_header=False, box=None, padding=(0, 2))
menu_table.add_column("Option", style="cyan bold", width=4)
menu_table.add_column("Description", style="white")

menu_table.add_row("1", "Analyze Company (with tech detection)")
menu_table.add_row("2", "Company Info Only")
menu_table.add_row("3", "Help & Documentation")
menu_table.add_row("4", "Exit")

console.print(menu_table)
console.print()

console.print("[dim]Select option [1-4]:[/dim]")
console.print()
console.print("[yellow]This is a preview of the interactive menu.[/yellow]")
console.print("[yellow]Run 'prism' with no arguments to use it interactively.[/yellow]")
