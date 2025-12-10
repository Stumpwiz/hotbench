"""
Data models for essays and evaluations
"""

import re
from pathlib import Path
from typing import Dict, Tuple, List

from hotbench.judges import JudgeScore
from hotbench.utils import count_words, format_score_breakdown
from hotbench.settings import ContestConfig, settings


class Essay:
    """Represents a student essay submission"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name

        # Extract student name from filename (firstnameLastname.txt)
        # Convert to "Firstname Lastname" format
        # Split on capital letters to separate firstname and Lastname
        # Pattern: match lowercase word(s) at start, then capture each capitalized word
        name_parts = re.findall(r'[a-z]+|[A-Z][a-z]*', filepath.stem)
        if len(name_parts) >= 2:
            # Capitalize first letter of each name part (firstname and Lastname)
            formatted_parts = [part.capitalize() for part in name_parts]
            # Truncate first name to 11 characters if longer
            if len(formatted_parts[0]) > 11:
                formatted_parts[0] = formatted_parts[0][:11]
            self.student_name = " ".join(formatted_parts)
        else:
            # Fallback to simple title case if pattern doesn't match
            name_raw = filepath.stem.replace("_", " ").replace("-", " ")
            self.student_name = name_raw.title()

        # Read essay content
        with open(filepath, 'r', encoding='utf-8') as f:
            self.content = f.read().strip()

        # Calculate word count
        self.word_count = count_words(self.content)

        # Check if essay exceeds word limit and should be disqualified
        self.is_disqualified = self.word_count > settings.MAX_WORD_COUNT
        self.disqualification_reason = (
            f"Exceeds word limit ({self.word_count}/{settings.MAX_WORD_COUNT} words)"
            if self.is_disqualified else None
        )

    def __repr__(self):
        status = " [DISQUALIFIED]" if self.is_disqualified else ""
        return f"Essay(student={self.student_name}, words={self.word_count}{status})"


class EssayEvaluation:
    """Complete evaluation of an essay by all judges"""

    def __init__(self, essay: Essay):
        self.essay = essay
        self.judge_scores: Dict[int, JudgeScore] = {}

    def add_judge_score(self, judge_id: int, score: JudgeScore):
        """Add a score from a judge"""
        self.judge_scores[judge_id] = score

    def get_total_score(self) -> int:
        """Get the total score across all judges"""
        return sum(score.total for score in self.judge_scores.values())

    def get_average_score(self) -> float:
        """Get average score per judge"""
        if not self.judge_scores:
            return 0.0
        return self.get_total_score() / len(self.judge_scores)

    def format_report_for_judge(self, judge_id: int) -> str:
        """Formats a text block for this essay's evaluation by a specific judge."""
        if judge_id not in self.judge_scores:
            return ""

        score = self.judge_scores[judge_id]
        report_lines = [
            "-" * 80,
            f"STUDENT: {self.essay.student_name}",
            f"WORD COUNT: {self.essay.word_count}",
            "-" * 80,
            "",
            "SCORES:",
            format_score_breakdown(score.model_dump()),
            "",
            "RATIONALE:",
            score.rationale,
            "\n"
        ]
        return "\n".join(report_lines)


class ConsolidatedResults:
    """Consolidated results across all judges"""

    def __init__(self, evaluations: List[EssayEvaluation], config: ContestConfig, output_dir: str):
        self.evaluations = evaluations
        self.config = config
        self.sorted_evaluations = sorted(
            evaluations,
            key=lambda e: e.get_total_score(),
            reverse=True
        )
        self.filepath: Path = Path(output_dir) / "final_results.txt"

    def get_winners(self) -> List[Tuple[int, EssayEvaluation]]:
        """Get top N winners (1st, 2nd, 3rd)"""
        num_winners = min(self.config.num_winners, len(self.sorted_evaluations))
        return [(i + 1, self.sorted_evaluations[i]) for i in range(num_winners)]
