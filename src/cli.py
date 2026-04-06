"""
Command-line interface for the pSEO Automation System.
Provides commands for database init, content generation, auditing, and monitoring.
"""
import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.models import init_db, get_session, PSEOPage, Tool, Category, BacklinkOpportunity

app = typer.Typer(
    name="pseo",
    help="pSEO Automation System - Programmatic SEO for AI Tool Websites",
    add_completion=False
)
console = Console()


@app.command("init")
def cmd_init():
    """Initialize the database and create all tables."""
    console.print(Panel("[bold green]Initializing pSEO database...[/bold green]"))
    init_db()
    console.print("[green]✓ Database initialized successfully![/green]")


@app.command("seed")
def cmd_seed():
    """Seed the database with sample AI tool data."""
    from src.engine.data_collector import DataCollector
    console.print(Panel("[bold blue]Seeding sample data...[/bold blue]"))
    collector = DataCollector()
    collector.seed_sample_data()
    collector.close()
    console.print("[green]✓ Sample data seeded successfully![/green]")


@app.command("generate")
def cmd_generate(
    page_type: str = typer.Option("alternative", help="Page type: alternative, comparison, listicle"),
    tool_slug: str = typer.Option(None, help="Target tool slug (for alternative/comparison)"),
    tool_b_slug: str = typer.Option(None, help="Second tool slug (for comparison)"),
    category_slug: str = typer.Option(None, help="Category slug (for listicle/batch alternative)"),
    batch: bool = typer.Option(False, help="Batch generate all alternatives in a category"),
):
    """Generate pSEO pages using LLM content engine."""
    from src.engine.page_assembler import PageAssembler

    assembler = PageAssembler()

    try:
        if batch and category_slug:
            console.print(f"[blue]Batch generating alternatives for category: {category_slug}[/blue]")
            pages = assembler.batch_generate_alternatives(category_slug)
            console.print(f"[green]✓ Generated {len(pages)} pages[/green]")

        elif page_type == "alternative" and tool_slug and category_slug:
            console.print(f"[blue]Generating alternative page for: {tool_slug}[/blue]")
            page = assembler.assemble_alternative_page(tool_slug, category_slug)
            if page:
                console.print(f"[green]✓ Created: {page.url_path} ({page.word_count} words)[/green]")
            else:
                console.print("[red]✗ Failed to generate page[/red]")

        elif page_type == "comparison" and tool_slug and tool_b_slug:
            console.print(f"[blue]Generating comparison: {tool_slug} vs {tool_b_slug}[/blue]")
            page = assembler.assemble_comparison_page(tool_slug, tool_b_slug)
            if page:
                console.print(f"[green]✓ Created: {page.url_path} ({page.word_count} words)[/green]")
            else:
                console.print("[red]✗ Failed to generate page[/red]")

        elif page_type == "listicle" and category_slug:
            console.print(f"[blue]Generating listicle for category: {category_slug}[/blue]")
            page = assembler.assemble_listicle_page(category_slug)
            if page:
                console.print(f"[green]✓ Created: {page.url_path} ({page.word_count} words)[/green]")
            else:
                console.print("[red]✗ Failed to generate page[/red]")

        else:
            console.print("[red]Invalid arguments. Use --help for usage.[/red]")

    finally:
        assembler.close()


@app.command("audit")
def cmd_audit(
    url: str = typer.Argument(help="URL to audit"),
):
    """Run SEO technical audit on a URL."""
    from src.checker.seo_auditor import SEOAuditor

    async def run():
        auditor = SEOAuditor()
        result = await auditor.audit_url(url)
        auditor.close()

        table = Table(title=f"SEO Audit: {url}")
        table.add_column("Check", style="cyan")
        table.add_column("Result", style="green")

        table.add_row("H1 Tags", str(result.h1_count))
        table.add_row("Has H1", "✓" if result.has_h1 else "✗")
        table.add_row("Meta Description", "✓" if result.has_meta_description else "✗")
        table.add_row("JSON-LD Schema", "✓" if result.has_schema else "✗")
        table.add_row("Missing Alt Tags", str(result.missing_alt_count))
        table.add_row("Broken Links", str(result.broken_links_count))
        table.add_row("Overall", "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]")

        console.print(table)

        if result.issues:
            console.print("\n[bold red]Issues Found:[/bold red]")
            for issue in result.issues:
                console.print(f"  • {issue}")

    asyncio.run(run())


@app.command("monitor")
def cmd_monitor(
    domains: str = typer.Argument(help="Comma-separated competitor domains"),
):
    """Run competitor monitoring and backlink discovery."""
    from src.monitor.competitor_monitor import CompetitorMonitor

    domain_list = [d.strip() for d in domains.split(",")]
    monitor = CompetitorMonitor()

    try:
        report = monitor.run_weekly_report(domain_list)

        table = Table(title="Competitor Monitor Report")
        table.add_column("Domain", style="cyan")
        table.add_column("DR", justify="right")
        table.add_column("Monthly Traffic", justify="right")
        table.add_column("New Opportunities", justify="right")
        table.add_column("High Quality", justify="right", style="green")

        for comp in report["competitors"]:
            table.add_row(
                comp["domain"],
                str(comp["domain_rating"]),
                f"{comp['monthly_traffic']:,}",
                str(comp["new_backlink_opportunities"]),
                str(comp["high_quality_opportunities"]),
            )

        console.print(table)
        console.print(f"\n[green]Total new opportunities: {report['total_new_opportunities']}[/green]")
        console.print(f"[green]High quality (DR 30-60): {report['high_quality_opportunities']}[/green]")

    finally:
        monitor.close()


@app.command("sitemap")
def cmd_sitemap(
    output: str = typer.Option("sitemap.xml", help="Output file path"),
    include_drafts: bool = typer.Option(False, help="Include draft pages"),
):
    """Generate sitemap.xml from published pages."""
    from src.checker.sitemap_generator import SitemapGenerator

    generator = SitemapGenerator()
    xml = generator.generate(output_path=output, include_drafts=include_drafts)
    generator.close()
    console.print(f"[green]✓ Sitemap generated: {output}[/green]")


@app.command("submit-index")
def cmd_submit_index(
    url: str = typer.Option(None, help="Single URL to submit"),
    all_published: bool = typer.Option(False, help="Submit all published pages"),
):
    """Submit URLs to Google Indexing API."""
    from src.checker.seo_auditor import GoogleIndexingSubmitter

    submitter = GoogleIndexingSubmitter()
    session = get_session()

    try:
        if url:
            success = submitter.submit_url(url)
            status = "[green]✓ Submitted[/green]" if success else "[red]✗ Failed[/red]"
            console.print(f"{status}: {url}")

        elif all_published:
            pages = session.query(PSEOPage).filter(PSEOPage.status == "Published").all()
            urls = [f"{settings.site_url}{p.url_path}" for p in pages]
            results = submitter.submit_batch(urls)
            console.print(f"[green]Submitted: {results['submitted']}[/green], [red]Failed: {results['failed']}[/red]")

        else:
            console.print("[red]Specify --url or --all-published[/red]")

    finally:
        submitter.close()
        session.close()


@app.command("list-pages")
def cmd_list_pages(
    status: str = typer.Option("all", help="Filter by status: all, Draft, Published"),
    limit: int = typer.Option(20, help="Max pages to show"),
):
    """List generated pSEO pages."""
    session = get_session()
    query = session.query(PSEOPage)
    if status != "all":
        query = query.filter(PSEOPage.status == status)
    pages = query.order_by(PSEOPage.created_at.desc()).limit(limit).all()

    table = Table(title=f"pSEO Pages ({status})")
    table.add_column("Type", style="cyan")
    table.add_column("URL Path")
    table.add_column("Keyword")
    table.add_column("Words", justify="right")
    table.add_column("Status", style="green")

    for page in pages:
        table.add_row(
            page.page_type,
            page.url_path,
            page.primary_keyword[:50],
            str(page.word_count),
            page.status
        )

    console.print(table)
    session.close()


@app.command("list-opportunities")
def cmd_list_opportunities(
    min_dr: int = typer.Option(30, help="Minimum domain rating"),
):
    """List discovered backlink opportunities."""
    from src.monitor.competitor_monitor import CompetitorMonitor

    monitor = CompetitorMonitor()
    opportunities = monitor.get_all_opportunities(min_dr=min_dr)

    table = Table(title=f"Backlink Opportunities (DR ≥ {min_dr})")
    table.add_column("DR", justify="right", style="green")
    table.add_column("Domain")
    table.add_column("URL")
    table.add_column("Type")
    table.add_column("Status")

    for opp in opportunities[:20]:
        table.add_row(
            str(opp.domain_rating),
            opp.source_domain,
            opp.source_url[:60] + "..." if len(opp.source_url) > 60 else opp.source_url,
            opp.link_type,
            opp.status
        )

    console.print(table)
    monitor.close()


if __name__ == "__main__":
    app()
