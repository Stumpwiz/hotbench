"""
Meta-analysis by a fifth LLM judge
"""

import os
from pathlib import Path
import openai
from openai.types.chat import ChatCompletion
from rich.console import Console

from hotbench.models import ConsolidatedResults
from hotbench.settings import ContestConfig, OUTPUT_DIR
from hotbench.utils import SCORE_CATEGORIES

console = Console()


class MetaAnalyzer:
    """Fifth LLM that analyzes the judging results"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = "gpt-4o-mini"  # Changed from gpt-4 to avoid rate limits

    @staticmethod
    def create_analysis_prompt(results: ConsolidatedResults, config: ContestConfig) -> str:
        """Create a prompt for meta-analysis"""

        # Compile all evaluation data
        data_summary = ["=" * 80, "BLACK HISTORY MONTH ESSAY CONTEST - JUDGING DATA", "=" * 80, "",
                        f"Total Essays Evaluated: {len(results.sorted_evaluations)}",
                        f"Number of Judges: {config.num_judges}", ""]

        # Winners
        winners = results.get_winners()
        data_summary.append("WINNERS:")
        for place, evaluation in winners:
            place_text = {1: "1st Place", 2: "2nd Place", 3: "3rd Place"}.get(place, f"{place}th Place")
            data_summary.append(f"  {place_text}: {evaluation.essay.student_name}")
            data_summary.append(f"    Total Score: {evaluation.get_total_score()}/{config.get_max_total_score()}")
            data_summary.append(
                f"    Judge Scores: {[evaluation.judge_scores[i].total for i in range(1, config.num_judges + 1)]}")

        data_summary.append("")
        data_summary.append("DETAILED EVALUATIONS:")
        data_summary.append("")

        # Detailed breakdown
        for rank, evaluation in enumerate(results.sorted_evaluations, 1):
            data_summary.append(f"\nESSAY #{rank}: {evaluation.essay.student_name}")
            data_summary.append(f"Word Count: {evaluation.essay.word_count}")
            data_summary.append(f"Total Score: {evaluation.get_total_score()}")
            data_summary.append("")

            max_score_per_judge = config.get_max_score_per_judge()
            for judge_id in range(1, config.num_judges + 1):
                if judge_id in evaluation.judge_scores:
                    score = evaluation.judge_scores[judge_id]
                    data_summary.append(f"  Judge {judge_id}:")
                    data_summary.append(f"  - Effectiveness: {score.effectiveness}/{SCORE_CATEGORIES['effectiveness']}")
                    data_summary.append(f"  - Creativity: {score.creativity}/{SCORE_CATEGORIES['creativity']}")
                    data_summary.append(f"  - Scholarship: {score.scholarship}/{SCORE_CATEGORIES['scholarship']}")
                    data_summary.append(f"  - Effort: {score.effort}/{SCORE_CATEGORIES['effort']}")
                    data_summary.append(f"  - Total: {score.total}/{max_score_per_judge}")
                    # Truncate rationale to 200 characters to reduce token usage
                    rationale_preview = score.rationale[:200] + "..." if len(score.rationale) > 200 else score.rationale
                    data_summary.append(f"  Rationale: {rationale_preview}")
                    data_summary.append("")

        prompt = f"""You are a meta-analyst reviewing the results of a Black History Month essay contest for middle school students.

Four different LLM judges evaluated each essay using this rubric:
{config.get_rubric_text()}

The judges were:
- Judge 1 (GPT-4): The Academic - focuses on scholarly rigor and historical accuracy
- Judge 2 (GPT-3.5-Turbo): The Creative Writer - emphasizes creative expression and originality
- Judge 3 (Gemini Pro): The Educator - considers age-appropriate expectations and developmental progress
- Judge 4 (GPT-4-Turbo): The Balanced Generalist - provides balanced evaluation across all criteria

Here is all the evaluation data:

{chr(10).join(data_summary)}

Please provide a comprehensive meta-analysis that addresses:

1. WINNING ESSAY ANALYSIS
   - What characteristics did the winning essays have in common?
   - What made them stand out from other submissions?
   - Were there any notable patterns in how different judges scored them?

2. JUDGE CONSISTENCY
   - How consistent were the judges in their evaluations?
   - Were there any notable disagreements or patterns?
   - Did certain judges tend to score higher or lower overall?
   - Did different judge types (Academic, Creative, Educator, Balanced) show different patterns?

3. RUBRIC EFFECTIVENESS
   - How well did the rubric distinguish between essays?
   - Were certain criteria more discriminating than others?
   - Did the point allocations seem appropriate?

4. DEVELOPMENTAL INSIGHTS
   - What does this contest reveal about middle school students' abilities?
   - Were word count and quality correlated?
   - What areas showed the most variation among students?

5. RECOMMENDATIONS
   - How could the rubric be improved for future contests?
   - What guidance would help students write stronger essays?
   - What training or calibration would help judges be more consistent?
   - Are there additional criteria that should be considered?

Please provide a thoughtful, detailed analysis with specific examples from the data.
"""
        return prompt

    def analyze(self, results: ConsolidatedResults, config: ContestConfig) -> str:
        """Perform meta-analysis of the results"""
        console.print("\n[bold blue]Generating meta-analysis...[/bold blue]")

        with console.status("[bold yellow]Fifth LLM analyzing results..."):
            try:
                # Build kwargs dict to handle the typing issue cleanly
                kwargs = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert educational researcher and statistician analyzing essay contest results. Provide thorough, insightful analysis with specific examples and actionable recommendations."
                        },
                        {
                            "role": "user",
                            "content": self.create_analysis_prompt(results, config)
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 3000
                }
                # The type checker understands unpacking a dictionary of arguments
                response = self.client.chat.completions.create(**kwargs)

                return self._parse_analysis_response(response)

            except Exception as e:
                console.print(f"[red]✗ Error generating meta-analysis: {str(e)}[/red]")
                return f"Error generating meta-analysis: {str(e)}"

    @staticmethod
    def _parse_analysis_response(response: ChatCompletion) -> str:
        """Safely parse the analysis from the API response."""
        if response.choices and response.choices[0].message:
            analysis = response.choices[0].message.content or ""
        else:
            analysis = "Meta-analysis could not be generated: API returned no choices."

        console.print("[green]✓ Meta-analysis complete[/green]")
        return analysis

    @staticmethod
    def save_analysis(analysis: str, output_dir: Path = None):
        """Save meta-analysis to a file"""
        output_path = output_dir or OUTPUT_DIR
        output_path.mkdir(parents=True, exist_ok=True)

        report_lines = ["=" * 80, "META-ANALYSIS BY FIFTH LLM JUDGE",
                        "Analyzing patterns, insights, and recommendations", "=" * 80, "", analysis, "", "=" * 80,
                        "END OF META-ANALYSIS", "=" * 80]

        analysis_file = output_path / "judge5.txt"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))

        console.print(f"[green]✓ Saved meta-analysis to {analysis_file}[/green]")


def perform_meta_analysis(results: ConsolidatedResults, config: ContestConfig, output_dir: Path = None) -> Path:
    """Perform and save meta-analysis"""
    analyzer = MetaAnalyzer()
    analysis = analyzer.analyze(results, config)
    output_path = output_dir or OUTPUT_DIR
    analyzer.save_analysis(analysis, output_path)
    return output_path / "judge5.txt"
