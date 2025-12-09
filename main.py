"""
Black History Month Essay Contest Judging System
Main entry point for the application
"""

import sys
from rich.console import Console
from rich.panel import Panel

from hotbench.settings import ContestConfig, ESSAY_DIR, OUTPUT_DIR
from hotbench.utils import load_environment, ensure_output_directory
from hotbench.llm import EssayEvaluator, consolidate_and_determine_winners
from hotbench.meta_judge import perform_meta_analysis

console = Console()


def print_banner():
    """Print welcome banner"""
    banner_text = """
[bold cyan]Black History Month Essay Contest[/bold cyan]
[bold white]Automated Judging System[/bold white]

Using AI to fairly evaluate middle school student essays
with multiple independent LLM judges.
"""
    console.print(Panel(banner_text, border_style="blue"))


def main():
    """Main execution flow"""
    try:
        # Print banner
        print_banner()

        # Load environment variables
        console.print("\n[bold]Step 1: Loading environment...[/bold]")
        load_environment()

        # Ensure output directory exists
        console.print("\n[bold]Step 2: Preparing output directory...[/bold]")
        ensure_output_directory(str(OUTPUT_DIR))
        console.print(f"[green]✓ Output directory ready: {OUTPUT_DIR}[/green]")

        # Initialize evaluator
        console.print("\n[bold]Step 3: Discovering essays...[/bold]")
        evaluator = EssayEvaluator()  # Uses defaults from settings
        essays = evaluator.discover_essays()

        if not essays:
            console.print("\n[yellow]No essays found to evaluate. Exiting.[/yellow]")
            console.print(f"\nPlease add essay files (firstnameLastname.txt) to {ESSAY_DIR}/")
            return

        # Create dynamic contest configuration
        num_judges = len(evaluator.judges)
        contest_config = ContestConfig(num_judges=num_judges)

        # Confirm with user
        console.print(f"\n[bold yellow]About to evaluate {len(essays)} essay(s) with {len(evaluator.judges)} judges.[/bold yellow]")
        console.print("[yellow]This will make API calls and may take several minutes.[/yellow]")

        response = console.input("\n[bold]Proceed? (yes/no): [/bold]").strip().lower()
        if response not in ['yes', 'y']:
            console.print("[yellow]Evaluation cancelled.[/yellow]")
            return

        # Evaluate all essays
        console.print("\n[bold]Step 4: Evaluating essays...[/bold]")
        evaluations = evaluator.evaluate_all_essays()

        if not evaluations:
            console.print("\n[red]No evaluations completed. Exiting.[/red]")
            return

        # Save individual judge reports
        console.print("\n[bold]Step 5: Saving judge reports...[/bold]")
        summary_report_file = evaluator.save_summary_report()
        judge_report_files = evaluator.save_judge_reports()

        # Consolidate scores and determine winners
        console.print("\n[bold]Step 6: Consolidating scores and determining winners...[/bold]")
        results = consolidate_and_determine_winners(evaluations, contest_config)

        # Perform meta-analysis
        console.print("\n[bold]Step 7: Generating meta-analysis...[/bold]")
        meta_analysis_file = perform_meta_analysis(results, contest_config)

        # Final summary
        console.print("\n" + "=" * 80)
        console.print("[bold green]EVALUATION COMPLETE![/bold green]")
        console.print("=" * 80)
        console.print(f"\nTotal essays evaluated: {len(evaluations)}")
        console.print(f"All output files saved to: {OUTPUT_DIR}/")
        console.print("\n[bold]Generated Files:[/bold]")
        for file_path in judge_report_files:
            console.print(f"  • {file_path.name}")
        console.print(f"  • {results.filepath.name}")
        console.print(f"  • {meta_analysis_file.name}")
        if summary_report_file:
            console.print(f"  • {summary_report_file.name}")

        winners = results.get_winners()
        if winners:
            console.print("\n[bold cyan]Winners:[/bold cyan]")
            for place, evaluation in winners:
                place_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "🏆")
                place_text = {1: "1st", 2: "2nd", 3: "3rd"}.get(place, f"{place}th")
                console.print(
                    f"  {place_emoji} {place_text} Place: [bold]{evaluation.essay.student_name}[/bold] "
                    f"({evaluation.get_total_score()} points)"
                )

        console.print("\n[bold green]Thank you for using the Essay Judging System![/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Evaluation interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]ERROR: {str(e)}[/bold red]")
        console.print("\nPlease check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
