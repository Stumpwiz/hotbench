"""
LLM evaluation logic and orchestration
"""

from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table

from hotbench.judges import get_all_judges, Judge
from hotbench.models import Essay, EssayEvaluation, ConsolidatedResults
from hotbench.utils import validate_essay_file, SCORE_CATEGORIES
from hotbench.settings import ContestConfig, ESSAY_DIR, OUTPUT_DIR

console = Console()


class EssayEvaluator:
    """Coordinates evaluation of all essays by all judges"""

    def __init__(self, essays_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.essays_dir = essays_dir or ESSAY_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.essays: List[Essay] = []
        self.evaluations: List[EssayEvaluation] = []
        self.judges: List[Judge] = get_all_judges()

    def discover_essays(self) -> List[Essay]:
        """Discover all essay text files in the directory"""
        console.print("\n[bold blue]Discovering essays...[/bold blue]")

        # Find all .txt files in the essays directory
        txt_files = [
            f for f in self.essays_dir.glob("*.txt") if validate_essay_file(f)
        ]

        self.essays = [Essay(f) for f in txt_files]
        self.essays.sort(key=lambda e: e.student_name)  # Sort for consistent order

        if not self.essays:
            console.print("[yellow]No essay files found![/yellow]")
            console.print(f"Place essay files as 'firstnameLastname.txt' in {self.essays_dir}/")
        else:
            console.print(f"[green]Found {len(self.essays)} essay(s):[/green]")
            for essay in self.essays:
                console.print(f"  • {essay.student_name} ({essay.word_count} words)")

        return self.essays

    def evaluate_all_essays(self) -> List[EssayEvaluation]:
        """Have all judges evaluate all essays"""
        if not self.essays:
            console.print("[red]No essays to evaluate![/red]")
            return []

        console.print(
            f"\n[bold blue]Evaluating {len(self.essays)} essay(s) with {len(self.judges)} judges...[/bold blue]")

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                transient=True,
        ) as progress:
            essay_task = progress.add_task("[cyan]Evaluating Essays", total=len(self.essays))

            for essay in self.essays:
                progress.update(essay_task, description=f"[cyan]Evaluating: {essay.student_name}")
                evaluation = EssayEvaluation(essay)

                judge_task = progress.add_task(f"[yellow]  Judges for {essay.student_name}", total=len(self.judges))
                for judge in self.judges:
                    progress.update(judge_task,
                                    description=f"[yellow]  Judge {judge.judge_id} for {essay.student_name}")
                    try:
                        score = judge.evaluate(essay.content, essay.student_name)
                        evaluation.add_judge_score(judge.judge_id, score)
                        progress.log(
                            f"  [green]✓[/green] Judge {judge.judge_id} scored '{essay.student_name}': {score.total} points")
                    except Exception as e:
                        progress.log(f"  [red]✗[/red] Judge {judge.judge_id} error on '{essay.student_name}': {str(e)}")
                    progress.advance(judge_task)

                self.evaluations.append(evaluation)
                progress.advance(essay_task)

        return self.evaluations

    def save_judge_reports(self) -> List[Path]:
        """Save individual judge reports to files"""
        saved_files = []
        self.output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"\n[bold blue]Saving judge reports to {self.output_dir}/[/bold blue]")

        # Create a report for each judge
        for judge in self.judges:
            report_lines = ["=" * 80, f"JUDGE {judge.judge_id}: {judge.judge_type.upper()}",
                            f"Model: {judge.model_name}", "=" * 80, ""]

            for evaluation in self.evaluations:
                report_lines.append(evaluation.format_report_for_judge(judge.judge_id))

            # Save to file
            report_file = self.output_dir / f"judge{judge.judge_id}.txt"
            with open(report_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write("\n".join(report_lines))

            saved_files.append(report_file)
            console.print(f"  ✓ Saved judge{judge.judge_id}.txt")

        return saved_files

    def save_summary_report(self) -> Optional[Path]:
        """Save a summary report of all evaluations"""
        if not self.evaluations:
            return None

        console.print(f"\n[bold blue]Saving summary report to {self.output_dir}/[/bold blue]")

        # Sort evaluations by average score, descending
        sorted_evaluations = sorted(self.evaluations, key=lambda e: e.get_average_score(), reverse=True)

        table = Table(title="Essay Evaluation Summary")
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Student", style="magenta")
        table.add_column("Word Count", justify="right")
        table.add_column("Avg. Score", style="green", justify="right")

        for i, evaluation in enumerate(sorted_evaluations):
            rank = f"{i + 1}"
            avg_score = f"{evaluation.get_average_score():.2f}"
            if i == 0:  # Highlight the winner
                rank = f"🏆 {rank}"
            table.add_row(rank, evaluation.essay.student_name, str(evaluation.essay.word_count), avg_score)

        console.print(table)

        # Save the summary to a file
        summary_file = self.output_dir / "summary_report.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            # We can reuse the rich console's capture feature to easily write the table to a file
            from rich.console import Console as FileConsole
            file_console = FileConsole(file=f, record=True, width=120)
            file_console.print(table)

        console.print(f"  ✓ Saved summary_report.md")

        return summary_file


def consolidate_and_determine_winners(evaluations: List[EssayEvaluation], config: ContestConfig,
                                     output_dir: Optional[Path] = None) -> ConsolidatedResults:
    """Consolidate scores and determine winners"""
    console.print("\n[bold blue]Consolidating scores and determining winners...[/bold blue]")

    output_path = output_dir or OUTPUT_DIR
    results = ConsolidatedResults(evaluations, config, str(output_path))
    _display_results(results)
    _save_results(results)

    return results


def _display_results(results: ConsolidatedResults):
    """Display consolidated results in a table"""
    console.print("\n[bold blue]" + "=" * 80 + "[/bold blue]")
    console.print("[bold blue]CONSOLIDATED RESULTS[/bold blue]")
    console.print("[bold blue]" + "=" * 80 + "[/bold blue]\n")

    # Create a result table
    table = Table(title="All Essays - Ranked by Total Score")
    table.add_column("Rank", style="cyan", justify="center")
    table.add_column("Student", style="magenta")
    table.add_column("Word Count", justify="right")
    for i in range(1, results.config.num_judges + 1):
        table.add_column(f"Judge {i}", justify="right")
    table.add_column("Total", justify="right", style="bold")
    table.add_column("Average", justify="right")

    for rank, evaluation in enumerate(results.sorted_evaluations, 1):
        scores = [
            str(evaluation.judge_scores.get(i, 0).total)
            for i in range(1, results.config.num_judges + 1)
        ]

        rank_display = f"#{rank}"
        if rank <= results.config.num_winners:
            if rank == 1:
                rank_display = "🥇 1st"
            elif rank == 2:
                rank_display = "🥈 2nd"
            elif rank == 3:
                rank_display = "🥉 3rd"

        row_data = [
            rank_display,
            evaluation.essay.student_name,
            str(evaluation.essay.word_count),
            *scores,  # Unpack all judge scores
            str(evaluation.get_total_score()),
            f"{evaluation.get_average_score():.1f}"
        ]
        table.add_row(*row_data)

    console.print(table)
    console.print()


def _save_results(results: ConsolidatedResults):
    """Save consolidated results to a file"""
    results.filepath.parent.mkdir(parents=True, exist_ok=True)

    report_lines = ["=" * 80, "BLACK HISTORY MONTH ESSAY CONTEST - FINAL RESULTS", "=" * 80, ""]

    # Winners section
    winners = results.get_winners()
    report_lines.append("WINNERS:")
    report_lines.append("-" * 80)
    for place, evaluation in winners:
        place_text = {1: "1ST PLACE", 2: "2ND PLACE", 3: "3RD PLACE"}.get(place, f"{place}TH PLACE")
        report_lines.append(f"\n{place_text}: {evaluation.essay.student_name}")
        report_lines.append(f"Total Score: {evaluation.get_total_score()}/{results.config.get_max_total_score()}")
        report_lines.append(f"Average Score: {evaluation.get_average_score():.1f}/{results.config.get_max_score_per_judge()}")
        report_lines.append("")
        report_lines.append("Individual Judge Scores: ")
        max_score_per_judge = results.config.get_max_score_per_judge()
        for judge_id in range(1, results.config.num_judges + 1):
            if judge_id in evaluation.judge_scores:
                score = evaluation.judge_scores[judge_id]
                report_lines.append(f"  Judge {judge_id}: {score.total}/{max_score_per_judge}")
                for category, max_val in SCORE_CATEGORIES.items():
                    actual_score = getattr(score, category, 0)
                    report_lines.append(f"    - {category.capitalize()}: {actual_score}/{max_val}")

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("ALL ESSAYS - RANKED")
    report_lines.append("=" * 80)
    report_lines.append("")

    # All essays table
    header_parts = [f"{'Rank':<8}", f"{'Student':<25}", f"{'Words':<8}"]
    header_parts.extend([f"J{i:<5}" for i in range(1, results.config.num_judges + 1)])
    header_parts.extend([f"{'Total':<8}", f"{'Avg':<8}"])
    header = " ".join(header_parts)
    report_lines.append(header)
    report_lines.append("-" * 80)

    for rank, evaluation in enumerate(results.sorted_evaluations, 1):
        scores = [
            evaluation.judge_scores.get(i, 0).total
            for i in range(1, results.config.num_judges + 1)
        ]

        row_parts = [f"{rank:<8}", f"{evaluation.essay.student_name:<25}", f"{evaluation.essay.word_count:<8}"]
        row_parts.extend([f"{s:<6}" for s in scores])
        row_parts.extend([f"{evaluation.get_total_score():<8}", f"{evaluation.get_average_score():<8.1f}"])
        row = " ".join(row_parts)
        report_lines.append(row)

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("DETAILED BREAKDOWN BY STUDENT")
    report_lines.append("=" * 80)
    report_lines.append("")

    for rank, evaluation in enumerate(results.sorted_evaluations, 1):
        report_lines.append("-" * 80)
        report_lines.append(f"RANK #{rank}: {evaluation.essay.student_name}")
        report_lines.append(f"Word Count: {evaluation.essay.word_count}")
        report_lines.append(f"Total Score: {evaluation.get_total_score()}/{results.config.get_max_total_score()}")
        report_lines.append("-" * 80)
        report_lines.append("")
        max_score_per_judge = results.config.get_max_score_per_judge()
        for judge_id in range(1, results.config.num_judges + 1):
            if judge_id in evaluation.judge_scores:
                score = evaluation.judge_scores[judge_id]
                report_lines.append(f"Judge {judge_id} - Total: {score.total}/{max_score_per_judge}")
                for category, max_val in SCORE_CATEGORIES.items():
                    actual_score = getattr(score, category, 0)
                    report_lines.append(f"  - {category.capitalize()}: {actual_score}/{max_val}")
                report_lines.append(f"  Brief Rationale: {score.rationale[:200]}...")
                report_lines.append("")

        report_lines.append("")

    # Save to file
    with open(results.filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    console.print(f"[green]✓ Saved consolidated results to {results.filepath}[/green]")
