"""
Utility functions for the essay judging system
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Define the scoring structure in one place for easy maintenance
SCORE_CATEGORIES = {
    "effectiveness": 25,
    "creativity": 25,
    "scholarship": 25,
    "effort": 10,
}


def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()

    # Check for required API keys
    required_keys = ["OPENAI_API_KEY", "GOOGLE_API_KEY"]
    optional_keys = ["LANGCHAIN_API_KEY", "WANDB_API_KEY"]

    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)

    if missing_keys:
        console.print("[bold red]ERROR: Missing required API keys![/bold red]")
        console.print(f"Missing: {', '.join(missing_keys)}")
        console.print("\nPlease set these in your .env file:")
        console.print("1. Copy .env.example to .env")
        console.print("2. Add your API keys to .env")
        raise EnvironmentError(f"Missing required API keys: {', '.join(missing_keys)}")

    console.print("[green]✓ Environment loaded successfully[/green]")

    # Warn about optional keys
    missing_optional = [key for key in optional_keys if not os.getenv(key)]
    if missing_optional:
        console.print(f"[yellow]Note: Optional keys not set: {', '.join(missing_optional)}[/yellow]")


def validate_essay_file(filepath: Path) -> bool:
    """Validate that a file is a valid essay submission"""
    return (
        filepath.exists()
        and filepath.is_file()
        and filepath.suffix == ".txt"
        and filepath.stat().st_size > 0
    )


def ensure_output_directory(output_dir: str = "data/outputs"):
    """Ensure output directory exists"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())


def format_score_breakdown(scores: dict) -> str:
    """Format score breakdown as a string"""
    lines = [
        f"{key.replace('_', ' ').capitalize()}: {scores.get(key, 0)}/{max_score}"
        for key, max_score in SCORE_CATEGORIES.items()
    ]

    total_max_score = sum(SCORE_CATEGORIES.values())
    lines.append(f"TOTAL: {scores.get('total', 0)}/{total_max_score}")

    return "\n".join(lines)
