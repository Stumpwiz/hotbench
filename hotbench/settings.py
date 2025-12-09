"""
Centralized configuration for the essay contest.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

from hotbench.utils import SCORE_CATEGORIES

# ----------------------------------------
# Project root paths
# ----------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ESSAY_DIR = DATA_DIR / "essays"
OUTPUT_DIR = DATA_DIR / "outputs"
LOG_DIR = DATA_DIR / "logs"


# ----------------------------------------
# Environment + Secrets
# ----------------------------------------

class Settings(BaseSettings):
    """
    Central configuration for Hotbench.
    Automatically loads:
    - .env file (if present)
    - OS environment variables
    """

    # API Keys
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Optional keys
    LANGCHAIN_API_KEY: Optional[str] = None
    WANDB_API_KEY: Optional[str] = None

    # Default LLM configuration
    MODEL_NAME: str = "gpt-4o-mini"

    # Judge configuration
    NUM_JUDGES: int = 4
    NUM_WINNERS: int = 3

    # Logging and output
    VERBOSE: bool = True

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra environment variables
    }


# Global settings instance
settings = Settings()


# ----------------------------------------
# Contest Configuration
# ----------------------------------------

class ContestConfig:
    """Configuration class for contest parameters."""

    def __init__(self, num_judges: Optional[int] = None, num_winners: Optional[int] = None):
        self.num_judges = num_judges or settings.NUM_JUDGES
        self.num_winners = num_winners or settings.NUM_WINNERS

    @staticmethod
    def get_max_score_per_judge() -> int:
        """Calculate the maximum possible score from a single judge."""
        return sum(SCORE_CATEGORIES.values())

    def get_max_total_score(self) -> int:
        """Calculate the maximum possible total score across all judges."""
        return self.get_max_score_per_judge() * self.num_judges

    @staticmethod
    def get_rubric_text() -> str:
        """Generate a string representation of the scoring rubric."""
        return "\n".join([
            f"- {key.replace('_', ' ').capitalize()}: {value} points"
            for key, value in SCORE_CATEGORIES.items()
        ])
