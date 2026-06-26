"""
Prism CLI interface.
Terminal UI built with Typer and Rich.
"""

import os
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

from prism.api.client import CrustDataClient
from prism.analyzer.tech_detector import TechStackDetector
from prism.models.company import Company, Employee, TechSignal
from prism.utils.llm import get_llm_client

# Load environment variables from .env file
load_dotenv()

# Create CLI app
app = typer.Typer(
    help="Prism - Reverse engineer tech stacks from hiring patterns",
    add_completion=False
)

console = Console()


def get_client() -> CrustDataClient:
    """
    Initialize API client with credentials from environment.
    """
    api_key = os.getenv("CRUSTDATA_API_KEY")
    if not api_key:
        console.print("[red]Error: CRUSTDATA_API_KEY not set in .env file[/red]")
        sys.exit(1)

    cache_dir = os.getenv("CACHE_DIR", ".cache")
    return CrustDataClient(api_key=api_key, cache_dir=cache_dir)


def _lookup_company(client: CrustDataClient, domain: str) -> Optional[Company]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(f"Identifying {domain}...", total=None)
        company = client.identify_company(domain)

        if company:
            progress.update(task, description=f"Found: {company.name}")

    if not company:
        console.print(f"[red]Error: Could not find company with domain '{domain}'[/red]")
        console.print("[yellow]Tip: Try the primary domain, e.g. 'stripe.com' instead of 'www.stripe.com'[/yellow]")

    return company


def _company_panel(company: Company) -> Panel:
    return Panel(
        f"[bold]{company.name}[/bold]\n"
        f"ID: {company.company_id}\n"
        f"Domain: {company.basic_info.primary_domain}\n"
        f"Founded: {company.basic_info.year_founded or 'Unknown'}\n"
        f"Size: {company.basic_info.employee_count_range or 'Unknown'}",
        title="Company Info",
        border_style="cyan"
    )


def _fetch_employees(
    client: CrustDataClient,
    company: Company,
    sample_size: int
) -> List[Employee]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(f"Fetching {sample_size} employee profiles...", total=None)
        employees = client.search_employees(company_name=company.name, limit=sample_size)

        if employees:
            progress.update(task, description=f"Analyzing {len(employees)} profiles...")

    if not employees:
        console.print(f"[red]Error: No employees found for {company.name}[/red]")
        console.print("[yellow]The company name from identify may not match employee records exactly.[/yellow]")

    return employees


def _confidence_bar(confidence: float, width: int = 20) -> str:
    filled = int(confidence * width)
    return "█" * filled + "░" * (width - filled)


def _confidence_color(confidence: float) -> str:
    if confidence >= 0.7:
        return "green"
    if confidence >= 0.4:
        return "yellow"
    return "red"


def _build_signal_tree(
    company_name: str,
    grouped_signals: Dict[str, List[TechSignal]],
    verbose: bool
) -> Tree:
    tree = Tree(f"[bold]{company_name} Tech Stack[/bold]")

    for category, category_signals in grouped_signals.items():
        category_branch = tree.add(f"[bold yellow]{category.upper()}[/bold yellow]")

        for signal in category_signals:
            color = _confidence_color(signal.confidence)
            tech_line = (
                f"[{color}]{signal.technology}[/{color}] "
                f"[dim]{_confidence_bar(signal.confidence)}[/dim] "
                f"[bold]{signal.confidence:.0%}[/bold] "
                f"[dim]({signal.evidence_count} profiles)[/dim]"
            )

            tech_branch = category_branch.add(tech_line)

            if verbose and signal.evidence:
                for evidence in signal.evidence[:3]:
                    tech_branch.add(f"[dim italic]{evidence}[/dim italic]")

    return tree


def _print_signal_summary(signals: List[TechSignal]) -> None:
    high = len([signal for signal in signals if signal.confidence > 0.7])
    medium = len([signal for signal in signals if 0.4 <= signal.confidence <= 0.7])
    low = len([signal for signal in signals if signal.confidence < 0.4])

    console.print(f"\n[dim]Total technologies detected: {len(signals)}[/dim]")
    console.print(f"[dim]High confidence (>70%): {high}[/dim]")
    console.print(f"[dim]Medium confidence (40-70%): {medium}[/dim]")
    console.print(f"[dim]Low confidence (<40%): {low}[/dim]\n")


def _llm_payload(grouped_signals: Dict[str, List[TechSignal]]) -> Dict[str, List[Dict]]:
    return {
        category: [
            {
                "technology": signal.technology,
                "confidence": signal.confidence,
                "evidence_count": signal.evidence_count
            }
            for signal in category_signals
        ]
        for category, category_signals in grouped_signals.items()
    }


def _render_insights(
    company: Company,
    grouped_signals: Dict[str, List[TechSignal]],
    employee_count: int
) -> None:
    console.print("[bold cyan]Generating Strategic Insights...[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("Consulting Claude via AWS Bedrock...", total=None)
        llm = get_llm_client()

        if not llm:
            console.print("[yellow]Warning: LLM client not available. Skipping insights.[/yellow]")
            return

        analysis = llm.analyze_tech_stack(
            company_name=company.name,
            tech_signals=_llm_payload(grouped_signals),
            employee_count=employee_count
        )

    if not analysis:
        console.print("[yellow]Could not generate insights. Check AWS Bedrock access.[/yellow]\n")
        return

    console.print(Panel(
        analysis,
        title="LLM Strategic Analysis",
        border_style="magenta",
        padding=(1, 2)
    ))
    console.print()


def run_analysis(
    domain: str,
    sample_size: int,
    verbose: bool = False,
    min_confidence: float = 0.1,
    insights: bool = False
) -> bool:
    console.print("\n[bold cyan]Prism Tech Stack Analyzer[/bold cyan]\n")

    client = get_client()
    company = _lookup_company(client, domain)
    if not company:
        return False

    console.print(_company_panel(company))

    employees = _fetch_employees(client, company, sample_size)
    if not employees:
        return False

    detector = TechStackDetector()
    signals = [
        signal
        for signal in detector.detect_tech_stack(employees)
        if signal.confidence >= min_confidence
    ]

    if not signals:
        console.print("[yellow]No technologies detected above confidence threshold[/yellow]")
        return False

    grouped = detector.group_by_category(signals)

    console.print("\n[bold green]Tech Stack Analysis[/bold green]")
    console.print(f"Based on {len(employees)} employee profiles\n")
    console.print(_build_signal_tree(company.name, grouped, verbose))
    _print_signal_summary(signals)

    if insights:
        _render_insights(company, grouped, len(employees))

    return True


@app.command()
def analyze(
    domain: str = typer.Argument(..., help="Company domain (e.g., stripe.com)"),
    sample_size: int = typer.Option(10, "--sample", "-n", help="Number of employees to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed evidence"),
    min_confidence: float = typer.Option(0.1, "--min-confidence", "-c", help="Minimum confidence to display"),
    insights: bool = typer.Option(False, "--insights", "-i", help="Generate LLM-powered strategic insights"),
):
    """
    Analyze a company's tech stack by reverse engineering employee profiles.

    Example:
        prism analyze stripe.com --sample 20 --verbose
    """
    run_analysis(
        domain=domain,
        sample_size=sample_size,
        verbose=verbose,
        min_confidence=min_confidence,
        insights=insights
    )


@app.command()
def info(domain: str):
    """
    Get basic company information without analysis.

    Example:
        prism info openai.com
    """
    console.print(f"\n[bold cyan]Company Information[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(f"Looking up {domain}...", total=None)

        client = get_client()
        company = client.identify_company(domain)

        if not company:
            console.print(f"[red]Error: Could not find company with domain '{domain}'[/red]")
            return

    # Create detailed info table
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", company.name)
    table.add_row("ID", str(company.company_id))
    table.add_row("Primary Domain", company.basic_info.primary_domain)
    table.add_row("All Domains", ", ".join(company.basic_info.all_domains))
    table.add_row("Website", company.basic_info.website or "Unknown")
    table.add_row("Founded", str(company.basic_info.year_founded or "Unknown"))
    table.add_row("Employee Count", company.basic_info.employee_count_range or "Unknown")
    table.add_row("Industries", ", ".join(company.basic_info.industries))

    if company.basic_info.description:
        table.add_row("Description", company.basic_info.description[:200] + "...")

    console.print(table)
    console.print()


@app.command()
def interactive():
    """
    Launch interactive menu mode.

    Examples:
        prism interactive
        prism  (with no arguments)
    """
    while True:
        console.clear()

        # Display banner
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

        # Get user choice
        choice = Prompt.ask(
            "Select option",
            choices=["1", "2", "3", "4"],
            default="1"
        )

        if choice == "1":
            # Analyze company
            console.print()
            domain = Prompt.ask("[cyan]Company domain[/cyan] (e.g., stripe.com)")

            sample_size = IntPrompt.ask(
                "[cyan]Sample size[/cyan] (employees to analyze)",
                default=10
            )

            use_insights = Confirm.ask(
                "[cyan]Generate AI insights?[/cyan] (uses AWS Bedrock)",
                default=False
            )

            verbose = Confirm.ask(
                "[cyan]Show detailed evidence?[/cyan]",
                default=False
            )

            console.print()

            try:
                run_analysis(
                    domain=domain,
                    sample_size=sample_size,
                    verbose=verbose,
                    min_confidence=0.1,
                    insights=use_insights
                )
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "2":
            # Company info
            console.print()
            domain = Prompt.ask("[cyan]Company domain[/cyan] (e.g., stripe.com)")
            console.print()

            try:
                info(domain)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "3":
            # Help
            console.clear()
            help_panel = Panel(
                """[bold]Prism - Tech Stack Analyzer[/bold]

[cyan]How it works:[/cyan]
1. Identifies company via domain
2. Fetches employee profiles
3. Analyzes job titles, descriptions, work history
4. Detects technologies with confidence scores
5. Optional: Generates strategic insights via AI

[cyan]Commands:[/cyan]
- prism analyze <domain> --sample 10 --insights
- prism info <domain>
- prism interactive

[cyan]Tips:[/cyan]
- Larger sample size = better accuracy
- Look for >70% confidence signals
- AI insights explain strategic implications
- Results are cached for repeated queries

[cyan]Examples:[/cyan]
- prism analyze stripe.com --sample 20
- prism info openai.com
- prism analyze anthropic.com --insights --verbose
                """,
                title="Documentation",
                border_style="green",
                padding=(1, 2)
            )
            console.print(help_panel)
            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "4":
            # Exit
            console.print("\n[cyan]Thanks for using Prism![/cyan]\n")
            break


def main():
    """Entry point for CLI"""
    # If no arguments provided, launch interactive mode
    if len(sys.argv) == 1:
        interactive()
    else:
        app()


if __name__ == "__main__":
    main()
